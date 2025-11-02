#!/usr/bin/env python3
"""
Interactive CLI client for MAVLink MCP Server

This script provides a simple command-line interface to control your drone
through the MCP server. It sends commands directly to the MCP server tools.
"""

import asyncio
import json
from pathlib import Path
import sys

# Add parent directory to path to import the server
sys.path.insert(0, str(Path(__file__).parent.parent))

from mavsdk import System
import os
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path)


class DroneController:
    """Simple direct controller for the drone (bypasses MCP for simplicity)"""
    
    def __init__(self):
        self.drone = None
        self.connected = False
    
    async def connect(self):
        """Connect to the drone"""
        address = os.environ.get("MAVLINK_ADDRESS", "")
        port = os.environ.get("MAVLINK_PORT", "14540")
        protocol = os.environ.get("MAVLINK_PROTOCOL", "udp").lower()
        
        if not address:
            print("❌ ERROR: MAVLINK_ADDRESS not set in .env file")
            return False
        
        print(f"🔌 Connecting to drone at {protocol}://{address}:{port}...")
        
        self.drone = System()
        connection_string = f"{protocol}://{address}:{port}"
        await self.drone.connect(system_address=connection_string)
        
        # Wait for connection
        async for state in self.drone.core.connection_state():
            if state.is_connected:
                print(f"✅ Connected to drone!")
                self.connected = True
                break
        
        # Wait for GPS lock
        print("🛰️  Waiting for GPS lock...")
        async for health in self.drone.telemetry.health():
            if health.is_global_position_ok or health.is_home_position_ok:
                print("✅ GPS lock acquired!")
                break
        
        return True
    
    async def arm(self):
        """Arm the drone"""
        if not self.connected:
            print("❌ Not connected to drone")
            return
        
        print("🔧 Arming drone...")
        await self.drone.action.arm()
        print("✅ Drone armed!")
    
    async def disarm(self):
        """Disarm the drone"""
        if not self.connected:
            print("❌ Not connected to drone")
            return
        
        print("🔧 Disarming drone...")
        await self.drone.action.disarm()
        print("✅ Drone disarmed!")
    
    async def takeoff(self, altitude: float = 10.0):
        """Take off to specified altitude"""
        if not self.connected:
            print("❌ Not connected to drone")
            return
        
        print(f"🚁 Taking off to {altitude}m...")
        await self.drone.action.set_takeoff_altitude(altitude)
        await self.drone.action.takeoff()
        print(f"✅ Takeoff command sent! Target altitude: {altitude}m")
    
    async def land(self):
        """Land the drone"""
        if not self.connected:
            print("❌ Not connected to drone")
            return
        
        print("🛬 Landing drone...")
        await self.drone.action.land()
        print("✅ Landing command sent!")
    
    async def get_position(self):
        """Get current position"""
        if not self.connected:
            print("❌ Not connected to drone")
            return
        
        async for position in self.drone.telemetry.position():
            print(f"📍 Position:")
            print(f"   Latitude:  {position.latitude_deg}°")
            print(f"   Longitude: {position.longitude_deg}°")
            print(f"   Altitude:  {position.relative_altitude_m}m")
            break
    
    async def get_battery(self):
        """Get battery status"""
        if not self.connected:
            print("❌ Not connected to drone")
            return
        
        async for battery in self.drone.telemetry.battery():
            print(f"🔋 Battery: {battery.remaining_percent * 100:.1f}%")
            break
    
    async def get_flight_mode(self):
        """Get current flight mode"""
        if not self.connected:
            print("❌ Not connected to drone")
            return
        
        async for mode in self.drone.telemetry.flight_mode():
            print(f"✈️  Flight Mode: {mode}")
            break


async def print_help():
    """Print available commands"""
    print("\n" + "="*60)
    print("📋 AVAILABLE COMMANDS")
    print("="*60)
    print("  connect         - Connect to the drone")
    print("  arm             - Arm the drone")
    print("  disarm          - Disarm the drone")
    print("  takeoff [alt]   - Take off to altitude (default: 10m)")
    print("  land            - Land the drone")
    print("  position        - Get current GPS position")
    print("  battery         - Get battery status")
    print("  mode            - Get current flight mode")
    print("  help            - Show this help message")
    print("  quit/exit       - Exit the program")
    print("="*60 + "\n")


async def main():
    """Main interactive loop"""
    print("="*60)
    print("🚁 MAVLink Drone Interactive Controller")
    print("="*60)
    print("\nThis is a direct controller that talks to your drone.")
    print("Type 'help' for available commands.\n")
    
    controller = DroneController()
    
    # Auto-connect on startup
    await controller.connect()
    
    await print_help()
    
    while True:
        try:
            # Get user input
            command = input("\n🎮 Command> ").strip().lower()
            
            if not command:
                continue
            
            parts = command.split()
            cmd = parts[0]
            args = parts[1:] if len(parts) > 1 else []
            
            # Process commands
            if cmd in ["quit", "exit"]:
                print("\n👋 Goodbye!")
                break
            
            elif cmd == "help":
                await print_help()
            
            elif cmd == "connect":
                await controller.connect()
            
            elif cmd == "arm":
                await controller.arm()
            
            elif cmd == "disarm":
                await controller.disarm()
            
            elif cmd == "takeoff":
                altitude = float(args[0]) if args else 10.0
                await controller.takeoff(altitude)
            
            elif cmd == "land":
                await controller.land()
            
            elif cmd == "position" or cmd == "pos":
                await controller.get_position()
            
            elif cmd == "battery" or cmd == "bat":
                await controller.get_battery()
            
            elif cmd == "mode":
                await controller.get_flight_mode()
            
            else:
                print(f"❌ Unknown command: {cmd}")
                print("Type 'help' for available commands")
        
        except KeyboardInterrupt:
            print("\n\n👋 Interrupted. Type 'quit' to exit.")
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!")

