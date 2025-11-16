# Add lifespan support for startup/shutdown with strong typing
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from mcp.server.fastmcp import Context, FastMCP
from typing import Tuple
from mavsdk import System
from mavsdk.mission import MissionItem, MissionPlan
import asyncio
import os
import logging
import math
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables from .env file
env_path = Path(__file__).parent.parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

# Configure logger
logger = logging.getLogger("MAVLinkMCP")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

@dataclass
class MAVLinkConnector:
    drone: System
    connection_ready: asyncio.Event = field(default_factory=asyncio.Event)

# Global connector instance - persists across all HTTP requests
_global_connector: MAVLinkConnector | None = None
_connection_task: asyncio.Task | None = None
_connection_lock = asyncio.Lock()

async def ensure_connection(connector: MAVLinkConnector, timeout: float = 30.0) -> bool:
    """
    Wait for the drone connection to be ready.
    
    Args:
        connector: The MAVLinkConnector instance
        timeout: Maximum time to wait in seconds
        
    Returns:
        bool: True if connected, False if timeout
    """
    try:
        await asyncio.wait_for(connector.connection_ready.wait(), timeout=timeout)
        return True
    except asyncio.TimeoutError:
        logger.error(f"Drone connection timeout after {timeout}s")
        return False

async def connect_drone_background(drone: System, address: str, port: str, protocol: str, connection_ready: asyncio.Event):
    """Connect to drone in the background without blocking server startup"""
    connection_string = f"{protocol}://{address}:{port}"
    logger.info("Background: Connecting to drone...")
    logger.info("  Protocol: %s", protocol.upper())
    logger.info("  Target: %s:%s", address, port)
    
    await drone.connect(system_address=connection_string)

    logger.info("Background: Waiting for drone to respond...")
    async for state in drone.core.connection_state():
        if state.is_connected:
            logger.info("=" * 60)
            logger.info("✓ SUCCESS: Connected to drone at %s:%s!", address, port)
            logger.info("=" * 60)
            break

    logger.info("Background: Waiting for GPS lock...")
    async for health in drone.telemetry.health():
        if health.is_global_position_ok or health.is_home_position_ok:
            logger.info("=" * 60)
            logger.info("✓ GPS LOCK ACQUIRED")
            logger.info("  Global position: %s", "OK" if health.is_global_position_ok else "Not ready")
            logger.info("  Home position: %s", "OK" if health.is_home_position_ok else "Not ready")
            logger.info("=" * 60)
            logger.info("Drone is READY for commands")
            logger.info("=" * 60)
            # Signal that connection is ready!
            connection_ready.set()
            break


async def get_or_create_global_connector() -> MAVLinkConnector:
    """Get or create the global drone connector (thread-safe)"""
    global _global_connector, _connection_task
    
    async with _connection_lock:
        if _global_connector is not None:
            return _global_connector
        
        # Initialize for the first time
        logger.info("=" * 60)
        logger.info("MAVLink MCP Server - Initializing Global Drone Connection")
        logger.info("=" * 60)
        
        # Read connection settings from environment (.env file)
        address = os.environ.get("MAVLINK_ADDRESS", "")
        port = os.environ.get("MAVLINK_PORT", "14540")
        protocol = os.environ.get("MAVLINK_PROTOCOL", "udp").lower()
        
        # Display connection configuration
        logger.info("Configuration loaded from .env file:")
        logger.info("  MAVLINK_ADDRESS: %s", address if address else "(not set)")
        logger.info("  MAVLINK_PORT: %s", port)
        logger.info("  MAVLINK_PROTOCOL: %s", protocol)
        logger.info("=" * 60)
        
        if not address:
            logger.warning("WARNING: MAVLINK_ADDRESS not set in .env file!")
            raise ValueError("MAVLINK_ADDRESS not configured in .env file")
        
        # Validate protocol
        if protocol not in ["tcp", "udp", "serial"]:
            logger.warning("Invalid protocol '%s', defaulting to udp", protocol)
            protocol = "udp"
        
        drone = System()
        connection_ready = asyncio.Event()
        
        # Create the global connector
        _global_connector = MAVLinkConnector(drone=drone, connection_ready=connection_ready)
        
        # Start drone connection in background
        logger.info("Starting persistent drone connection in background...")
        logger.info("This connection will be shared across all requests")
        logger.info("-" * 60)
        
        _connection_task = asyncio.create_task(
            connect_drone_background(drone, address, port, protocol, connection_ready)
        )
        
        return _global_connector

@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[MAVLinkConnector]:
    """Manage application lifecycle - returns global persistent connector"""
    logger.info("=" * 60)
    logger.info("🚀 LIFESPAN: Starting application lifespan...")
    logger.info("=" * 60)
    
    try:
        # Get or create the global connector (only happens once)
        logger.info("LIFESPAN: Calling get_or_create_global_connector()...")
        connector = await get_or_create_global_connector()
        logger.info("LIFESPAN: Connector created successfully!")
        
        # Just yield the global connector - no teardown per request!
        yield connector
    except Exception as e:
        logger.error("❌ LIFESPAN ERROR: %s", str(e), exc_info=True)
        raise
    
    # Note: cleanup only happens on server shutdown (not per request)
    # In HTTP mode, this might not be called at all until process termination
    logger.info("LIFESPAN: Shutting down...")

# Pass lifespan to server
mcp = FastMCP("MAVLink MCP", lifespan=app_lifespan)


# ============================================================
# Startup Hook for SSE Mode
# ============================================================
async def initialize_drone_connection():
    """
    Initialize the global drone connection.
    Call this from mavlinkmcp_http.py after the server starts.
    """
    logger.info("=" * 60)
    logger.info("🚀 STARTUP: Initializing drone connection...")
    logger.info("=" * 60)
    try:
        await get_or_create_global_connector()
        logger.info("✓ Drone connection initialization complete!")
    except Exception as e:
        logger.error("❌ Failed to initialize drone connection: %s", str(e), exc_info=True)


# ARM
@mcp.tool()
async def arm_drone(ctx: Context) -> dict:
    """Arm the drone. Waits for drone connection if not yet ready."""
    connector = ctx.request_context.lifespan_context
    
    # Wait for connection
    if not await ensure_connection(connector):
        return {"status": "failed", "error": "Drone connection timeout. Please wait and try again."}
    
    drone = connector.drone
    logger.info("Arming")
    await drone.action.arm()
    return {"status": "success", "message": "Drone armed"}


# Get Position
@mcp.tool()
async def get_position(ctx: Context) -> dict:
    """
    Get the position of the drone in latitude/longitude degrees and altitude in meters.
    The drone must be connected and have a global position estimate.
    This tool will wait up to 30 seconds for the drone to be ready.

    Args:
        ctx (Context): The context of the request.

    Returns:
        dict: A dict with the position or error status.
    """
    connector = ctx.request_context.lifespan_context
    
    # Wait for connection
    if not await ensure_connection(connector):
        return {"status": "failed", "error": "Drone connection timeout. Please wait and try again."}
    
    drone = connector.drone
    logger.info("Fetching drone position")

    try:
        async for position in drone.telemetry.position():
            return {"status": "success", "position": {
                "latitude_deg": position.latitude_deg,
                "longitude_deg": position.longitude_deg,
                "absolute_altitude_m": position.absolute_altitude_m,
                "relative_altitude_m": position.relative_altitude_m
            }}
    except Exception as e:
        logger.error(f"Failed to retrieve position: {e}")
        return {"status": "failed", "error": str(e)}

@mcp.tool()
async def move_to_relative(ctx: Context, north_m: float, east_m: float, down_m: float, yaw_deg: float = 0.0) -> dict:
    """
    Move the drone relative to the current position using ArduPilot's GUIDED mode.
    
    ArduPilot automatically enters GUIDED mode when receiving goto_location commands
    (as long as the drone is armed). No manual mode switching required.
    
    The drone must be armed and in the air. Waits for connection if not ready.

    Args:
        ctx (Context): the context.
        north_m (float): distance in meters to move north (negative for south).
        east_m (float): distance in meters to move east (negative for west).
        down_m (float): distance in meters to move down (negative for up). Note: negative values = climb.
        yaw_deg (float): target yaw angle in degrees. Default is 0.0 (no yaw change).

    Returns:
        dict: Status message with success or error.
    """
    connector = ctx.request_context.lifespan_context
    
    # Wait for connection
    if not await ensure_connection(connector):
        return {"status": "failed", "error": "Drone connection timeout. Please wait and try again."}
    
    drone = connector.drone

    try:
        # Get current position
        position = await drone.telemetry.position().__anext__()
        current_lat = position.latitude_deg
        current_lon = position.longitude_deg
        # IMPORTANT: goto_location() requires ABSOLUTE altitude (MSL), not relative!
        current_alt = position.absolute_altitude_m
        
        # Calculate target altitude (down is positive in NED, so negate)
        target_alt = current_alt - down_m
        
        # Convert NED offsets (meters) to lat/lon offsets (degrees)
        # Earth radius in meters (approximate)
        EARTH_RADIUS = 6371000.0
        
        # Latitude: 1 degree = ~111,320 meters (constant)
        # north_m positive = increase latitude
        lat_offset_deg = north_m / 111320.0
        
        # Longitude: varies with latitude
        # east_m positive = increase longitude
        lon_offset_deg = east_m / (111320.0 * math.cos(math.radians(current_lat)))
        
        # Calculate target position
        target_lat = current_lat + lat_offset_deg
        target_lon = current_lon + lon_offset_deg
        
        logger.info(f"Moving in GUIDED mode:")
        logger.info(f"  Current: {current_lat:.6f}°, {current_lon:.6f}°")
        logger.info(f"  Altitude: {current_alt:.1f}m MSL (absolute) | {position.relative_altitude_m:.1f}m AGL (relative)")
        logger.info(f"  Offset: north={north_m:.1f}m, east={east_m:.1f}m, down={down_m:.1f}m")
        logger.info(f"  Target: {target_lat:.6f}°, {target_lon:.6f}°, {target_alt:.1f}m MSL")
        
        # Use goto_location with calculated target coordinates
        await drone.action.goto_location(
            target_lat,
            target_lon,
            target_alt,
            yaw_deg
        )
        
        logger.info("✓ Movement command sent successfully")
        return {
            "status": "success", 
            "message": f"Moving: north={north_m}m, east={east_m}m, altitude_change={-down_m}m",
            "target_position": {
                "latitude_deg": target_lat,
                "longitude_deg": target_lon,
                "altitude_m": target_alt
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to execute relative movement: {e}")
        return {"status": "failed", "error": f"Movement failed: {str(e)}"}

@mcp.tool()
async def takeoff(ctx: Context, takeoff_altitude: float = 3.0) -> dict:
    """Command the drone to initiate takeoff and ascend to a specified altitude. The drone must be armed. Waits for connection if not ready.

    Args:
        ctx (Context): The context of the request.
        takeoff_altitude (float): The altitude to ascend to after takeoff. Default is 3.0 meters.

    Returns:
        dict: Status message with success or error.
    """
    connector = ctx.request_context.lifespan_context
    
    # Wait for connection
    if not await ensure_connection(connector):
        return {"status": "failed", "error": "Drone connection timeout. Please wait and try again."}
    
    drone = connector.drone
    logger.info("Initiating takeoff")
    await drone.action.set_takeoff_altitude(takeoff_altitude)
    await drone.action.takeoff()
    return {"status": "success", "message": f"Takeoff initiated to {takeoff_altitude}m"}

@mcp.tool()
async def land(ctx: Context) -> dict:
    """Command the drone to initiate landing at its current location. Waits for connection if not ready.

    Args:
        ctx (Context): The context of the request.

    Returns:
        dict: Status message with success or error.
    """
    connector = ctx.request_context.lifespan_context
    
    # Wait for connection
    if not await ensure_connection(connector):
        return {"status": "failed", "error": "Drone connection timeout. Please wait and try again."}
    
    drone = connector.drone
    logger.info("Initiating landing")
    await drone.action.land()
    return {"status": "success", "message": "Landing initiated"}

@mcp.tool()
async def print_status_text(ctx: Context) -> dict:
    """Print and return status text from the drone. Waits for connection if not ready."""
    connector = ctx.request_context.lifespan_context
    
    # Wait for connection
    if not await ensure_connection(connector):
        return {"status": "failed", "error": "Drone connection timeout. Please wait and try again."}
    
    drone = connector.drone
    try:
        async for status_text in drone.telemetry.status_text():
            logger.info(f"Status: {status_text.type}: {status_text.text}")
            return {"status": "success", "type": status_text.type, "text": status_text.text}
    except asyncio.CancelledError:
        return {"status": "failed", "error": "Failed to retrieve status text"}

@mcp.tool()
async def get_imu(ctx: Context, n: int = 1) -> dict:
    """Fetch the first n IMU data points from the drone. Waits for connection if not ready.

    Args:
        ctx (Context): The context of the request.
        n (int): The number of IMU data points to fetch. Default is 1.

    Returns:
        dict: A dict with status and list of IMU data points.
    """
    connector = ctx.request_context.lifespan_context
    
    # Wait for connection
    if not await ensure_connection(connector):
        return {"status": "failed", "error": "Drone connection timeout. Please wait and try again."}
    
    drone = connector.drone
    telemetry = drone.telemetry

    # Set the rate at which IMU data is updated (in Hz)
    await telemetry.set_rate_imu(200.0)

    imu_data = []
    count = 0

    async for imu in telemetry.imu():
        imu_data.append({
            "timestamp_us": imu.timestamp_us,
            "acceleration": {
                "x": imu.acceleration_frd.forward_m_s2,
                "y": imu.acceleration_frd.right_m_s2,
                "z": imu.acceleration_frd.down_m_s2
            },
            "angular_velocity": {
                "x": imu.angular_velocity_frd.forward_rad_s,
                "y": imu.angular_velocity_frd.right_rad_s,
                "z": imu.angular_velocity_frd.down_rad_s
            },
            "magnetic_field": {
                "x": imu.magnetic_field_frd.forward_gauss,
                "y": imu.magnetic_field_frd.right_gauss,
                "z": imu.magnetic_field_frd.down_gauss
            },
            "temperature_degc": imu.temperature_degc
        })
        count += 1
        if count >= n:
            break

    return {"status": "success", "imu_data": imu_data, "count": len(imu_data)}

@mcp.tool()
async def print_mission_progress(ctx: Context) -> dict:
    """
    Print and return the current mission progress of the drone. Waits for connection if not ready.

    Args:
        ctx (Context): The context of the request.

    Returns:
        dict: A dictionary containing the current and total mission progress or error status.
    """
    connector = ctx.request_context.lifespan_context
    
    # Wait for connection
    if not await ensure_connection(connector):
        return {"status": "failed", "error": "Drone connection timeout. Please wait and try again."}
    
    drone = connector.drone
    async for mission_progress in drone.mission.mission_progress():
        logger.info(f"Mission progress: {mission_progress.current}/{mission_progress.total}")
        return {"status": "success", "current": mission_progress.current, "total": mission_progress.total}



@mcp.tool()
async def initiate_mission(ctx: Context, mission_points: list, return_to_launch: bool = True) -> dict:
    """
    Initiate a mission with a list of mission points. The drone must be armed. Waits for connection if not ready.

    Args:
        ctx (Context): The context of the request.
        mission_points (list): A list of dictionaries representing mission points. Each dictionary must include:
            - latitude_deg (float): Latitude in degrees (range: -90 to +90).
            - longitude_deg (float): Longitude in degrees (range: -180 to +180).
            - relative_altitude_m (float): Altitude relative to the takeoff altitude in meters.
            - speed_m_s (float): Speed in meters per second.
            - is_fly_through (bool): Whether to fly through the point or stop.
            - gimbal_pitch_deg (float): Gimbal pitch angle in degrees (optional).
            - gimbal_yaw_deg (float): Gimbal yaw angle in degrees (optional).
            - camera_action (MissionItem.CameraAction): Camera action at the point (optional).
            - loiter_time_s (float): Loiter time in seconds (optional).
            - camera_photo_interval_s (float): Camera photo interval in seconds (optional).
            - acceptance_radius_m (float): Acceptance radius in meters (optional).
            - yaw_deg (float): Yaw angle in degrees (optional).
            - camera_photo_distance_m (float): Camera photo distance in meters (optional).
            - vehicle_action (MissionItem.VehicleAction): Vehicle action at the point (optional).
        return_to_launch (bool): Whether to return to launch after completing the mission. Default is True.

    Returns:
        dict: Status message with success or error.
    """
    connector = ctx.request_context.lifespan_context
    
    # Wait for connection
    if not await ensure_connection(connector):
        return {"status": "failed", "error": "Drone connection timeout. Please wait and try again."}
    
    drone = connector.drone

    # Validate and construct mission items
    mission_items = []
    for point in mission_points:
        try:
            # Validate latitude and longitude ranges
            if not (-90 <= point["latitude_deg"] <= 90):
                return {"status": "failed", "error": f"Invalid latitude_deg: {point['latitude_deg']}. Must be between -90 and 90."}
            if not (-180 <= point["longitude_deg"] <= 180):
                return {"status": "failed", "error": f"Invalid longitude_deg: {point['longitude_deg']}. Must be between -180 and 180."}

            mission_items.append(MissionItem(
                latitude_deg=point["latitude_deg"],
                longitude_deg=point["longitude_deg"],
                relative_altitude_m=point["relative_altitude_m"],
                speed_m_s=point["speed_m_s"],
                is_fly_through=point["is_fly_through"],
                gimbal_pitch_deg=point.get("gimbal_pitch_deg", float('nan')),
                gimbal_yaw_deg=point.get("gimbal_yaw_deg", float('nan')),
                camera_action=point.get("camera_action", MissionItem.CameraAction.NONE),
                loiter_time_s=point.get("loiter_time_s", float('nan')),
                camera_photo_interval_s=point.get("camera_photo_interval_s", float('nan')),
                acceptance_radius_m=point.get("acceptance_radius_m", float('nan')),
                yaw_deg=point.get("yaw_deg", float('nan')),
                camera_photo_distance_m=point.get("camera_photo_distance_m", float('nan')),
                vehicle_action=point.get("vehicle_action", MissionItem.VehicleAction.NONE)
            ))
        except KeyError as e:
            return {"status": "failed", "error": f"Missing required field in mission point: {e}"}

    mission_plan = MissionPlan(mission_items)

    # Set return-to-launch behavior
    await drone.mission.set_return_to_launch_after_mission(return_to_launch)

    logger.info("Uploading mission")
    await drone.mission.upload_mission(mission_plan)

    logger.info("Starting mission")
    await drone.mission.start_mission()

    return {"status": "success", "message": f"Mission started with {len(mission_items)} waypoints"}

@mcp.tool()
async def get_flight_mode(ctx: Context) -> dict:
    """
    Get the current flight mode of the drone. Waits for connection if not ready.

    Args:
        ctx (Context): The context of the request.

    Returns:
        dict: The current flight mode of the drone or error status.
    """
    connector = ctx.request_context.lifespan_context
    
    # Wait for connection
    if not await ensure_connection(connector):
        return {"status": "failed", "error": "Drone connection timeout. Please wait and try again."}
    
    drone = connector.drone
    try:
        flight_mode = await drone.telemetry.flight_mode().__anext__()
        logger.info(f"FlightMode: {flight_mode}")
        return {"status": "success", "flight_mode": str(flight_mode)}
    except StopAsyncIteration:
        logger.error("Failed to retrieve flight mode")
        return {"status": "failed", "error": "Failed to retrieve flight mode"}

# ============================================================================
# PRIORITY 1: CRITICAL SAFETY TOOLS (v1.1.0)
# ============================================================================

@mcp.tool()
async def disarm_drone(ctx: Context) -> dict:
    """
    Disarm the drone motors. This stops the motors from spinning.
    SAFETY: Only use when drone is on the ground!
    Waits for connection if not ready.

    Args:
        ctx (Context): The context of the request.

    Returns:
        dict: Status message with success or error.
    """
    connector = ctx.request_context.lifespan_context
    
    # Wait for connection
    if not await ensure_connection(connector):
        return {"status": "failed", "error": "Drone connection timeout. Please wait and try again."}
    
    drone = connector.drone
    logger.info("Disarming drone")
    
    try:
        await drone.action.disarm()
        return {"status": "success", "message": "Drone disarmed - motors stopped"}
    except Exception as e:
        logger.error(f"Failed to disarm: {e}")
        return {"status": "failed", "error": f"Disarm failed: {str(e)}"}

@mcp.tool()
async def return_to_launch(ctx: Context) -> dict:
    """
    Command the drone to return to its launch/home position (RTL mode).
    This is the primary emergency/safety feature.
    The drone will fly back to home and land automatically.
    Waits for connection if not ready.

    Args:
        ctx (Context): The context of the request.

    Returns:
        dict: Status message with success or error.
    """
    connector = ctx.request_context.lifespan_context
    
    # Wait for connection
    if not await ensure_connection(connector):
        return {"status": "failed", "error": "Drone connection timeout. Please wait and try again."}
    
    drone = connector.drone
    logger.info("Initiating Return to Launch (RTL)")
    
    try:
        await drone.action.return_to_launch()
        return {"status": "success", "message": "Return to Launch initiated - drone returning home"}
    except Exception as e:
        logger.error(f"RTL failed: {e}")
        return {"status": "failed", "error": f"Return to Launch failed: {str(e)}"}

@mcp.tool()
async def kill_motors(ctx: Context) -> dict:
    """
    EMERGENCY ONLY: Immediately cut power to all motors.
    ⚠️  WARNING: This will cause the drone to fall from the sky!
    ⚠️  Only use in critical emergencies (fire, collision imminent, etc.)
    ⚠️  Drone may be damaged from the fall!
    Waits for connection if not ready.

    Args:
        ctx (Context): The context of the request.

    Returns:
        dict: Status message with success or error.
    """
    connector = ctx.request_context.lifespan_context
    
    # Wait for connection
    if not await ensure_connection(connector):
        return {"status": "failed", "error": "Drone connection timeout. Please wait and try again."}
    
    drone = connector.drone
    logger.warning("⚠️  EMERGENCY MOTOR KILL ACTIVATED ⚠️")
    
    try:
        await drone.action.kill()
        return {
            "status": "success", 
            "message": "EMERGENCY: Motors killed - drone will fall!",
            "warning": "This is an emergency action. Drone may be damaged."
        }
    except Exception as e:
        logger.error(f"Motor kill failed: {e}")
        return {"status": "failed", "error": f"Motor kill failed: {str(e)}"}

@mcp.tool()
async def hold_position(ctx: Context) -> dict:
    """
    Command the drone to hold its current position (loiter/hover mode).
    Useful for pausing during flight to assess situation or wait.
    Waits for connection if not ready.

    Args:
        ctx (Context): The context of the request.

    Returns:
        dict: Status message with success or error.
    """
    connector = ctx.request_context.lifespan_context
    
    # Wait for connection
    if not await ensure_connection(connector):
        return {"status": "failed", "error": "Drone connection timeout. Please wait and try again."}
    
    drone = connector.drone
    logger.info("Commanding drone to hold position")
    
    try:
        await drone.action.hold()
        return {"status": "success", "message": "Drone holding position (hovering/loitering)"}
    except Exception as e:
        logger.error(f"Hold position failed: {e}")
        return {"status": "failed", "error": f"Hold position failed: {str(e)}"}

@mcp.tool()
async def get_battery(ctx: Context) -> dict:
    """
    Get the current battery status including voltage and remaining percentage.
    Critical for monitoring flight time and knowing when to land.
    Waits for connection if not ready.

    Args:
        ctx (Context): The context of the request.

    Returns:
        dict: Battery voltage (V), remaining percentage (%), and status.
    """
    connector = ctx.request_context.lifespan_context
    
    # Wait for connection
    if not await ensure_connection(connector):
        return {"status": "failed", "error": "Drone connection timeout. Please wait and try again."}
    
    drone = connector.drone
    logger.info("Fetching battery status")
    
    try:
        async for battery in drone.telemetry.battery():
            battery_data = {
                "voltage_v": battery.voltage_v,
                "remaining_percent": battery.remaining_percent * 100,  # Convert to percentage
            }
            
            # Add warning if battery is low
            if battery.remaining_percent < 0.20:
                battery_data["warning"] = "⚠️  LOW BATTERY - Land soon!"
            elif battery.remaining_percent < 0.30:
                battery_data["warning"] = "Battery getting low - consider landing"
            
            logger.info(f"Battery: {battery_data['voltage_v']:.2f}V, {battery_data['remaining_percent']:.1f}%")
            return {"status": "success", "battery": battery_data}
    except Exception as e:
        logger.error(f"Failed to get battery status: {e}")
        return {"status": "failed", "error": f"Battery read failed: {str(e)}"}

# ============================================================================
# PRIORITY 2: FLIGHT MODE MANAGEMENT & SYSTEM HEALTH (v1.1.0)
# ============================================================================

@mcp.tool()
async def get_health(ctx: Context) -> dict:
    """
    Get comprehensive system health status for pre-flight checks.
    Returns status of GPS, accelerometer, gyro, magnetometer, and more.
    Waits for connection if not ready.

    Args:
        ctx (Context): The context of the request.

    Returns:
        dict: Comprehensive health status of all drone subsystems.
    """
    connector = ctx.request_context.lifespan_context
    
    # Wait for connection
    if not await ensure_connection(connector):
        return {"status": "failed", "error": "Drone connection timeout. Please wait and try again."}
    
    drone = connector.drone
    logger.info("Fetching system health")
    
    try:
        async for health in drone.telemetry.health():
            health_data = {
                "is_gyrometer_calibrated": health.is_gyrometer_calibration_ok,
                "is_accelerometer_calibrated": health.is_accelerometer_calibration_ok,
                "is_magnetometer_calibrated": health.is_magnetometer_calibration_ok,
                "is_local_position_ok": health.is_local_position_ok,
                "is_global_position_ok": health.is_global_position_ok,
                "is_home_position_ok": health.is_home_position_ok,
                "is_armable": health.is_armable,
            }
            
            # Add overall health assessment
            all_ok = all(health_data.values())
            health_data["overall_status"] = "HEALTHY" if all_ok else "ISSUES DETECTED"
            
            # Add warnings for critical issues
            warnings = []
            if not health.is_global_position_ok:
                warnings.append("⚠️  No GPS lock - cannot fly safely!")
            if not health.is_armable:
                warnings.append("⚠️  Drone is not armable - check for errors")
            if not health.is_gyrometer_calibration_ok:
                warnings.append("Gyroscope needs calibration")
            if not health.is_accelerometer_calibration_ok:
                warnings.append("Accelerometer needs calibration")
            if not health.is_magnetometer_calibration_ok:
                warnings.append("Magnetometer/compass needs calibration")
            
            if warnings:
                health_data["warnings"] = warnings
            
            logger.info(f"System health: {health_data['overall_status']}")
            return {"status": "success", "health": health_data}
    except Exception as e:
        logger.error(f"Failed to get health status: {e}")
        return {"status": "failed", "error": f"Health check failed: {str(e)}"}

@mcp.tool()
async def pause_mission(ctx: Context) -> dict:
    """
    Pause the currently executing mission.
    The drone will hold its position. Use resume_mission to continue.
    Waits for connection if not ready.

    Args:
        ctx (Context): The context of the request.

    Returns:
        dict: Status message with success or error.
    """
    connector = ctx.request_context.lifespan_context
    
    # Wait for connection
    if not await ensure_connection(connector):
        return {"status": "failed", "error": "Drone connection timeout. Please wait and try again."}
    
    drone = connector.drone
    logger.info("Pausing mission")
    
    try:
        await drone.mission.pause_mission()
        return {"status": "success", "message": "Mission paused - use resume_mission to continue"}
    except Exception as e:
        logger.error(f"Failed to pause mission: {e}")
        return {"status": "failed", "error": f"Mission pause failed: {str(e)}"}

@mcp.tool()
async def resume_mission(ctx: Context) -> dict:
    """
    Resume a previously paused mission.
    The drone will continue from where it was paused.
    Waits for connection if not ready.

    Args:
        ctx (Context): The context of the request.

    Returns:
        dict: Status message with success or error.
    """
    connector = ctx.request_context.lifespan_context
    
    # Wait for connection
    if not await ensure_connection(connector):
        return {"status": "failed", "error": "Drone connection timeout. Please wait and try again."}
    
    drone = connector.drone
    logger.info("Resuming mission")
    
    try:
        await drone.mission.start_mission()
        return {"status": "success", "message": "Mission resumed"}
    except Exception as e:
        logger.error(f"Failed to resume mission: {e}")
        return {"status": "failed", "error": f"Mission resume failed: {str(e)}"}

@mcp.tool()
async def clear_mission(ctx: Context) -> dict:
    """
    Clear the current mission from the drone.
    Removes all uploaded waypoints.
    Waits for connection if not ready.

    Args:
        ctx (Context): The context of the request.

    Returns:
        dict: Status message with success or error.
    """
    connector = ctx.request_context.lifespan_context
    
    # Wait for connection
    if not await ensure_connection(connector):
        return {"status": "failed", "error": "Drone connection timeout. Please wait and try again."}
    
    drone = connector.drone
    logger.info("Clearing mission")
    
    try:
        await drone.mission.clear_mission()
        return {"status": "success", "message": "Mission cleared - all waypoints removed"}
    except Exception as e:
        logger.error(f"Failed to clear mission: {e}")
        return {"status": "failed", "error": f"Mission clear failed: {str(e)}"}

# ============================================================================
# PRIORITY 3: NAVIGATION ENHANCEMENTS (v1.1.0)
# ============================================================================

@mcp.tool()
async def go_to_location(ctx: Context, latitude_deg: float, longitude_deg: float, 
                        absolute_altitude_m: float, yaw_deg: float = float('nan')) -> dict:
    """
    Fly to an absolute GPS location with specified altitude.
    This is direct waypoint navigation to specific coordinates.
    Waits for connection if not ready.

    Args:
        ctx (Context): The context of the request.
        latitude_deg (float): Target latitude in degrees (-90 to +90).
        longitude_deg (float): Target longitude in degrees (-180 to +180).
        absolute_altitude_m (float): Target altitude in meters above sea level (MSL).
        yaw_deg (float): Target yaw/heading in degrees (optional, default: maintain current heading).

    Returns:
        dict: Status message with success or error.
    """
    connector = ctx.request_context.lifespan_context
    
    # Wait for connection
    if not await ensure_connection(connector):
        return {"status": "failed", "error": "Drone connection timeout. Please wait and try again."}
    
    # Validate coordinates
    if not (-90 <= latitude_deg <= 90):
        return {"status": "failed", "error": f"Invalid latitude: {latitude_deg}. Must be between -90 and 90."}
    if not (-180 <= longitude_deg <= 180):
        return {"status": "failed", "error": f"Invalid longitude: {longitude_deg}. Must be between -180 and 180."}
    
    drone = connector.drone
    logger.info(f"Flying to GPS location: {latitude_deg}, {longitude_deg} at {absolute_altitude_m}m MSL")
    
    try:
        await drone.action.goto_location(latitude_deg, longitude_deg, absolute_altitude_m, yaw_deg)
        return {
            "status": "success", 
            "message": f"Flying to location",
            "target": {
                "latitude": latitude_deg,
                "longitude": longitude_deg,
                "altitude_msl": absolute_altitude_m,
                "yaw": yaw_deg if not math.isnan(yaw_deg) else "maintain current"
            }
        }
    except Exception as e:
        logger.error(f"Go to location failed: {e}")
        return {"status": "failed", "error": f"Navigation failed: {str(e)}"}

@mcp.tool()
async def get_home_position(ctx: Context) -> dict:
    """
    Get the home position where Return to Launch (RTL) will return to.
    This is typically set at the launch location when the drone first arms.
    Waits for connection if not ready.

    Args:
        ctx (Context): The context of the request.

    Returns:
        dict: Home position coordinates and altitude.
    """
    connector = ctx.request_context.lifespan_context
    
    # Wait for connection
    if not await ensure_connection(connector):
        return {"status": "failed", "error": "Drone connection timeout. Please wait and try again."}
    
    drone = connector.drone
    logger.info("Fetching home position")
    
    try:
        async for home in drone.telemetry.home():
            home_data = {
                "latitude_deg": home.latitude_deg,
                "longitude_deg": home.longitude_deg,
                "absolute_altitude_m": home.absolute_altitude_m,
            }
            logger.info(f"Home position: {home_data['latitude_deg']}, {home_data['longitude_deg']} at {home_data['absolute_altitude_m']}m")
            return {"status": "success", "home": home_data}
    except Exception as e:
        logger.error(f"Failed to get home position: {e}")
        return {"status": "failed", "error": f"Home position read failed: {str(e)}"}

@mcp.tool()
async def set_max_speed(ctx: Context, speed_m_s: float) -> dict:
    """
    Set the maximum speed limit for the drone.
    Useful for safety or when flying in confined areas.
    Waits for connection if not ready.

    Args:
        ctx (Context): The context of the request.
        speed_m_s (float): Maximum speed in meters per second. Typical range: 1-20 m/s.

    Returns:
        dict: Status message with success or error.
    """
    connector = ctx.request_context.lifespan_context
    
    # Wait for connection
    if not await ensure_connection(connector):
        return {"status": "failed", "error": "Drone connection timeout. Please wait and try again."}
    
    # Validate speed
    if speed_m_s <= 0:
        return {"status": "failed", "error": f"Invalid speed: {speed_m_s}. Must be positive."}
    if speed_m_s > 30:
        return {"status": "failed", "error": f"Speed too high: {speed_m_s} m/s. Maximum is 30 m/s for safety."}
    
    drone = connector.drone
    logger.info(f"Setting maximum speed to {speed_m_s} m/s")
    
    try:
        await drone.action.set_maximum_speed(speed_m_s)
        return {
            "status": "success", 
            "message": f"Maximum speed set to {speed_m_s} m/s",
            "speed_kmh": round(speed_m_s * 3.6, 1)  # Also provide in km/h
        }
    except Exception as e:
        logger.error(f"Failed to set max speed: {e}")
        return {"status": "failed", "error": f"Set max speed failed: {str(e)}"}

# ============================================================================
# PRIORITY 4: TELEMETRY & MONITORING (v1.1.0)
# ============================================================================

@mcp.tool()
async def get_speed(ctx: Context) -> dict:
    """
    Get the current ground speed (velocity over ground).
    Returns velocity in North, East, Down directions.
    Waits for connection if not ready.

    Args:
        ctx (Context): The context of the request.

    Returns:
        dict: Current velocity in NED frame and total ground speed.
    """
    connector = ctx.request_context.lifespan_context
    
    # Wait for connection
    if not await ensure_connection(connector):
        return {"status": "failed", "error": "Drone connection timeout. Please wait and try again."}
    
    drone = connector.drone
    logger.info("Fetching ground speed")
    
    try:
        async for velocity in drone.telemetry.velocity_ned():
            # Calculate total ground speed (horizontal speed only)
            ground_speed_m_s = math.sqrt(velocity.north_m_s**2 + velocity.east_m_s**2)
            
            speed_data = {
                "north_m_s": velocity.north_m_s,
                "east_m_s": velocity.east_m_s,
                "down_m_s": velocity.down_m_s,
                "ground_speed_m_s": round(ground_speed_m_s, 2),
                "ground_speed_kmh": round(ground_speed_m_s * 3.6, 2),
            }
            
            logger.info(f"Ground speed: {speed_data['ground_speed_m_s']} m/s ({speed_data['ground_speed_kmh']} km/h)")
            return {"status": "success", "velocity": speed_data}
    except Exception as e:
        logger.error(f"Failed to get speed: {e}")
        return {"status": "failed", "error": f"Speed read failed: {str(e)}"}

@mcp.tool()
async def get_attitude(ctx: Context) -> dict:
    """
    Get the current attitude (orientation) of the drone.
    Returns roll, pitch, and yaw angles in degrees.
    Waits for connection if not ready.

    Args:
        ctx (Context): The context of the request.

    Returns:
        dict: Roll, pitch, yaw angles in degrees.
    """
    connector = ctx.request_context.lifespan_context
    
    # Wait for connection
    if not await ensure_connection(connector):
        return {"status": "failed", "error": "Drone connection timeout. Please wait and try again."}
    
    drone = connector.drone
    logger.info("Fetching attitude")
    
    try:
        async for attitude in drone.telemetry.attitude_euler():
            attitude_data = {
                "roll_deg": round(attitude.roll_deg, 2),
                "pitch_deg": round(attitude.pitch_deg, 2),
                "yaw_deg": round(attitude.yaw_deg, 2),
            }
            
            logger.info(f"Attitude: roll={attitude_data['roll_deg']}°, pitch={attitude_data['pitch_deg']}°, yaw={attitude_data['yaw_deg']}°")
            return {"status": "success", "attitude": attitude_data}
    except Exception as e:
        logger.error(f"Failed to get attitude: {e}")
        return {"status": "failed", "error": f"Attitude read failed: {str(e)}"}

@mcp.tool()
async def get_gps_info(ctx: Context) -> dict:
    """
    Get detailed GPS information including number of satellites and fix type.
    Important for assessing navigation quality.
    Waits for connection if not ready.

    Args:
        ctx (Context): The context of the request.

    Returns:
        dict: GPS satellite count, fix type, and quality metrics.
    """
    connector = ctx.request_context.lifespan_context
    
    # Wait for connection
    if not await ensure_connection(connector):
        return {"status": "failed", "error": "Drone connection timeout. Please wait and try again."}
    
    drone = connector.drone
    logger.info("Fetching GPS info")
    
    try:
        async for gps_info in drone.telemetry.gps_info():
            gps_data = {
                "num_satellites": gps_info.num_satellites,
                "fix_type": str(gps_info.fix_type),
            }
            
            # Add quality assessment
            if gps_info.num_satellites >= 10:
                gps_data["quality"] = "Excellent"
            elif gps_info.num_satellites >= 6:
                gps_data["quality"] = "Good"
            elif gps_info.num_satellites >= 4:
                gps_data["quality"] = "Marginal"
            else:
                gps_data["quality"] = "Poor"
                gps_data["warning"] = "⚠️  Insufficient satellites for reliable navigation!"
            
            logger.info(f"GPS: {gps_data['num_satellites']} satellites, {gps_data['fix_type']}, {gps_data['quality']}")
            return {"status": "success", "gps": gps_data}
    except Exception as e:
        logger.error(f"Failed to get GPS info: {e}")
        return {"status": "failed", "error": f"GPS info read failed: {str(e)}"}

@mcp.tool()
async def get_in_air(ctx: Context) -> dict:
    """
    Check if the drone is currently in the air (flying) or on the ground.
    Waits for connection if not ready.

    Args:
        ctx (Context): The context of the request.

    Returns:
        dict: Boolean indicating if drone is airborne.
    """
    connector = ctx.request_context.lifespan_context
    
    # Wait for connection
    if not await ensure_connection(connector):
        return {"status": "failed", "error": "Drone connection timeout. Please wait and try again."}
    
    drone = connector.drone
    logger.info("Checking if drone is in air")
    
    try:
        async for in_air in drone.telemetry.in_air():
            status_text = "IN AIR (flying)" if in_air else "ON GROUND"
            logger.info(f"Drone status: {status_text}")
            return {
                "status": "success", 
                "in_air": in_air,
                "status_text": status_text
            }
    except Exception as e:
        logger.error(f"Failed to check in_air status: {e}")
        return {"status": "failed", "error": f"In-air check failed: {str(e)}"}

@mcp.tool()
async def get_armed(ctx: Context) -> dict:
    """
    Check if the drone is currently armed (motors can spin).
    Waits for connection if not ready.

    Args:
        ctx (Context): The context of the request.

    Returns:
        dict: Boolean indicating if drone is armed.
    """
    connector = ctx.request_context.lifespan_context
    
    # Wait for connection
    if not await ensure_connection(connector):
        return {"status": "failed", "error": "Drone connection timeout. Please wait and try again."}
    
    drone = connector.drone
    logger.info("Checking if drone is armed")
    
    try:
        async for armed in drone.telemetry.armed():
            status_text = "ARMED (motors ready)" if armed else "DISARMED (motors off)"
            logger.info(f"Drone status: {status_text}")
            return {
                "status": "success", 
                "armed": armed,
                "status_text": status_text
            }
    except Exception as e:
        logger.error(f"Failed to check armed status: {e}")
        return {"status": "failed", "error": f"Armed check failed: {str(e)}"}

# ============================================================================
# v1.2.0: PARAMETER MANAGEMENT
# ============================================================================

@mcp.tool()
async def get_parameter(ctx: Context, name: str, param_type: str = "auto") -> dict:
    """
    Get the value of a drone parameter by name.
    Parameters control drone behavior (e.g., flight speeds, sensor settings).
    Waits for connection if not ready.

    Args:
        ctx (Context): The context of the request.
        name (str): Parameter name (e.g., "RTL_ALT", "WPNAV_SPEED", "BATT_CAPACITY").
        param_type (str): Type of parameter - "int", "float", or "auto" (default: auto).
                          If "auto", will try float first, then int.

    Returns:
        dict: Parameter value and type, or error if parameter not found.
    
    Examples:
        - get_parameter("RTL_ALT", "float") - Get return-to-launch altitude
        - get_parameter("BATT_CAPACITY", "int") - Get battery capacity in mAh
        - get_parameter("WPNAV_SPEED") - Auto-detect parameter type
    """
    connector = ctx.request_context.lifespan_context
    
    # Wait for connection
    if not await ensure_connection(connector):
        return {"status": "failed", "error": "Drone connection timeout. Please wait and try again."}
    
    drone = connector.drone
    logger.info(f"Getting parameter: {name} (type: {param_type})")
    
    try:
        if param_type == "int":
            value = await drone.param.get_param_int(name)
            return {
                "status": "success",
                "name": name,
                "value": value,
                "type": "int"
            }
        elif param_type == "float":
            value = await drone.param.get_param_float(name)
            return {
                "status": "success",
                "name": name,
                "value": value,
                "type": "float"
            }
        else:  # auto-detect
            # Try float first (most common)
            try:
                value = await drone.param.get_param_float(name)
                return {
                    "status": "success",
                    "name": name,
                    "value": value,
                    "type": "float"
                }
            except:
                # If float fails, try int
                value = await drone.param.get_param_int(name)
                return {
                    "status": "success",
                    "name": name,
                    "value": value,
                    "type": "int"
                }
    except Exception as e:
        logger.error(f"Failed to get parameter {name}: {e}")
        return {
            "status": "failed", 
            "error": f"Parameter '{name}' not found or inaccessible: {str(e)}",
            "suggestion": "Check parameter name spelling. Use list_parameters to see available parameters."
        }

@mcp.tool()
async def set_parameter(ctx: Context, name: str, value: float, param_type: str = "auto") -> dict:
    """
    Set the value of a drone parameter by name.
    ⚠️ WARNING: Changing parameters can affect flight behavior. Only modify if you know what you're doing!
    Waits for connection if not ready.

    Args:
        ctx (Context): The context of the request.
        name (str): Parameter name (e.g., "RTL_ALT", "WPNAV_SPEED").
        value (float): New parameter value.
        param_type (str): Type of parameter - "int", "float", or "auto" (default: auto).
                          If "auto", will detect based on value (int if no decimal).

    Returns:
        dict: Confirmation of parameter change with old and new values.
    
    Examples:
        - set_parameter("RTL_ALT", 1500.0, "float") - Set RTL altitude to 15m
        - set_parameter("BATT_CAPACITY", 5200, "int") - Set battery capacity to 5200 mAh
    
    ⚠️ CAUTION: 
        - Invalid parameters can make the drone unflyable
        - Always verify values are within safe ranges
        - Consider backing up parameters before changes
        - Some parameters require reboot to take effect
    """
    connector = ctx.request_context.lifespan_context
    
    # Wait for connection
    if not await ensure_connection(connector):
        return {"status": "failed", "error": "Drone connection timeout. Please wait and try again."}
    
    drone = connector.drone
    logger.warning(f"⚠️ Setting parameter: {name} = {value} (type: {param_type})")
    
    try:
        # Get old value first
        try:
            if param_type == "int" or (param_type == "auto" and value == int(value)):
                old_value = await drone.param.get_param_int(name)
                param_type_final = "int"
            else:
                old_value = await drone.param.get_param_float(name)
                param_type_final = "float"
        except:
            old_value = None
            # Assume float if we can't get old value
            param_type_final = "float" if param_type == "auto" else param_type
        
        # Set new value
        if param_type_final == "int":
            await drone.param.set_param_int(name, int(value))
        else:
            await drone.param.set_param_float(name, float(value))
        
        logger.info(f"✓ Parameter {name} changed from {old_value} to {value}")
        
        return {
            "status": "success",
            "name": name,
            "old_value": old_value,
            "new_value": int(value) if param_type_final == "int" else float(value),
            "type": param_type_final,
            "message": f"Parameter '{name}' set to {value}",
            "warning": "Some parameters may require a reboot to take effect."
        }
    except Exception as e:
        logger.error(f"Failed to set parameter {name}: {e}")
        return {
            "status": "failed", 
            "error": f"Failed to set parameter '{name}': {str(e)}",
            "suggestion": "Verify parameter name and value are valid for this drone."
        }

@mcp.tool()
async def list_parameters(ctx: Context, filter_prefix: str = "") -> dict:
    """
    List all available drone parameters.
    This can return a large number of parameters (100-1000+).
    Optionally filter by prefix to narrow results.
    Waits for connection if not ready.

    Args:
        ctx (Context): The context of the request.
        filter_prefix (str): Optional prefix to filter parameters (e.g., "BATT" for battery params).
                            Leave empty to get all parameters.

    Returns:
        dict: List of all parameters with their names, values, and types.
    
    Examples:
        - list_parameters() - Get ALL parameters (may be very long!)
        - list_parameters("RTL") - Get all Return-to-Launch parameters
        - list_parameters("BATT") - Get all battery-related parameters
        - list_parameters("WPNAV") - Get all waypoint navigation parameters
    
    Common Parameter Prefixes:
        - RTL_ : Return to Launch settings
        - BATT_ : Battery settings
        - WPNAV_ : Waypoint navigation
        - EK2_ / EK3_ : EKF (Extended Kalman Filter) settings
        - COMPASS_ : Compass/magnetometer settings
        - GPS_ : GPS settings
    """
    connector = ctx.request_context.lifespan_context
    
    # Wait for connection
    if not await ensure_connection(connector):
        return {"status": "failed", "error": "Drone connection timeout. Please wait and try again."}
    
    drone = connector.drone
    logger.info(f"Listing parameters{f' (filter: {filter_prefix}*)' if filter_prefix else ''}")
    
    try:
        all_params = await drone.param.get_all_params()
        
        # Filter if prefix provided
        if filter_prefix:
            filter_upper = filter_prefix.upper()
            filtered = []
            for param in all_params.int_params:
                if param.name.upper().startswith(filter_upper):
                    filtered.append({"name": param.name, "value": param.value, "type": "int"})
            for param in all_params.float_params:
                if param.name.upper().startswith(filter_upper):
                    filtered.append({"name": param.name, "value": param.value, "type": "float"})
            
            filtered.sort(key=lambda x: x["name"])
            logger.info(f"Found {len(filtered)} parameters matching '{filter_prefix}*'")
            
            return {
                "status": "success",
                "filter": filter_prefix,
                "count": len(filtered),
                "parameters": filtered
            }
        else:
            # Return all parameters
            params_list = []
            for param in all_params.int_params:
                params_list.append({"name": param.name, "value": param.value, "type": "int"})
            for param in all_params.float_params:
                params_list.append({"name": param.name, "value": param.value, "type": "float"})
            
            params_list.sort(key=lambda x: x["name"])
            logger.info(f"Found {len(params_list)} total parameters")
            
            return {
                "status": "success",
                "count": len(params_list),
                "parameters": params_list,
                "warning": f"This is a large list ({len(params_list)} parameters). Consider using filter_prefix to narrow results."
            }
    except Exception as e:
        logger.error(f"Failed to list parameters: {e}")
        return {"status": "failed", "error": f"Failed to retrieve parameters: {str(e)}"}


if __name__ == "__main__":
    # Run the server
    mcp.run(transport='stdio')