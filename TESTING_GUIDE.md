# MAVLink MCP Testing Guide

Comprehensive test scenarios for v1.2.0 features using ChatGPT natural language control.

## Prerequisites

Before testing, ensure:
1. ✅ MAVLink MCP server is running (`./start_http_server.sh`)
2. ✅ Drone/SITL is connected and GPS lock acquired
3. ✅ ChatGPT is connected to your MCP server via ngrok HTTPS
4. ✅ You're in an open, safe area for testing

---

## 🎯 Comprehensive Test Scenario - Tower Inspection Mission

This test exercises **all 35 tools** including the 10 new v1.2.0 features.

### Copy this prompt into ChatGPT:

```
I need to conduct a detailed inspection of a cell tower. Here's what I need you to do:

PHASE 1 - PRE-FLIGHT CONFIGURATION:
1. First, show me all the RTL (Return to Launch) parameters currently configured
2. Check what the current RTL altitude is set to
3. If RTL altitude is less than 30 meters, set it to 30 meters for safety
4. Show me the battery capacity parameter and tell me what it's set to
5. Run a complete health check to make sure we're ready to fly

PHASE 2 - MISSION PREPARATION:
6. I want to create a 4-waypoint inspection mission around the tower. Upload (but don't start yet) a mission with these waypoints:
   - Waypoint 1: Approach point at lat 33.6459, lon -117.8427, altitude 20m
   - Waypoint 2: North side at lat 33.6460, lon -117.8427, altitude 30m  
   - Waypoint 3: East side at lat 33.6460, lon -117.8426, altitude 40m
   - Waypoint 4: Return to approach at lat 33.6459, lon -117.8427, altitude 20m

7. Download the mission back from the drone to verify it uploaded correctly

PHASE 3 - FLIGHT OPERATIONS:
8. Arm the drone and take off to 15 meters
9. Check our current position and battery level
10. Fly to the first waypoint position (lat 33.6459, lon -117.8427) and hold there at 20m
11. Rotate the drone to face due east (90 degrees) so the camera is pointing at the tower
12. Now orbit around the tower base at a 25 meter radius, moving at 3 m/s, centered on lat 33.6460, lon -117.8427 at 25m altitude, going clockwise
13. After 30 seconds of orbiting, tell me what our current speed is
14. Check the battery level again - if it's below 70%, I want you to warn me

PHASE 4 - DETAILED INSPECTION:
15. Stop the orbit and reposition to lat 33.6460, lon -117.8426 at 40m altitude to get a closer view of the upper tower section
16. Face north (0 degrees) to align with the tower
17. Get our current attitude (roll, pitch, yaw) to confirm we're level and facing the right direction

PHASE 5 - MISSION EXECUTION:
18. Now start the 4-waypoint mission we uploaded earlier
19. Monitor the mission and tell me when we reach waypoint 2
20. At waypoint 2, pause the mission temporarily
21. Check if the mission is finished (it shouldn't be since we paused it)
22. Resume the mission and let it continue
23. Keep checking until the mission is finished

PHASE 6 - RETURN AND LANDING:
24. Once mission is complete, check battery one more time
25. If battery is above 40%, orbit one more time around lat 33.6460, lon -117.8427 at 30m radius at 15m altitude, counter-clockwise at 2 m/s
26. Return to launch position
27. Land the drone
28. Disarm when safely on the ground

PHASE 7 - POST-FLIGHT:
29. Download the mission from the drone one more time to save it
30. Show me all parameters that changed during the flight (compare with initial values)

Please execute this entire inspection mission step by step, confirming each action before moving to the next. Warn me immediately if any step fails or if battery gets critically low.
```

### What This Tests

**Parameter Management (v1.2.0):**
- ✅ `list_parameters` - List RTL parameters
- ✅ `get_parameter` - Check RTL_ALT and battery capacity
- ✅ `set_parameter` - Modify RTL altitude if needed

**Advanced Navigation (v1.2.0):**
- ✅ `orbit_location` - Circle tower at 25m radius (clockwise then counter-clockwise)
- ✅ `set_yaw` - Face east (90°), then north (0°)
- ✅ `reposition` - Move to inspection position and hold

**Mission Enhancements (v1.2.0):**
- ✅ `upload_mission` - Upload 4-waypoint mission without starting
- ✅ `download_mission` - Verify upload and save at end
- ✅ `set_current_waypoint` - (implicitly tested with pause/resume)
- ✅ `is_mission_finished` - Check completion status

**Existing Features:**
- Flight control (arm, takeoff, land, disarm, hold)
- Safety (return_to_launch, battery monitoring)
- Navigation (go_to_location, get_position)
- Mission management (pause, resume, progress)
- Telemetry (health, speed, attitude, battery)

---

## 🔬 Granular Tool Test (Complete Coverage)

This test systematically validates **all 35 tools** one at a time with pass/fail reporting for each.

### Copy this prompt into ChatGPT:

```
I need you to test every single MCP tool available for drone control. Test each tool individually and report PASS or FAIL for each one. Follow this exact sequence and confirm each step before moving to the next.

SAFETY RULE: Before disarming, you MUST check altitude is below 0.5m AND drone is landed. Never disarm in the air.

═══════════════════════════════════════════════════════════
CATEGORY 1: TELEMETRY & HEALTH (Test before flight)
═══════════════════════════════════════════════════════════

TEST 1: get_health
- Run get_health and show me the full report
- Verify: GPS, accelerometer, gyroscope, magnetometer status
- Expected: All systems should be operational
- Report: PASS/FAIL

TEST 2: get_telemetry  
- Run get_telemetry
- Verify: Shows position, altitude, velocity, battery
- Expected: All telemetry fields populated
- Report: PASS/FAIL

TEST 3: get_battery
- Run get_battery
- Verify: Shows voltage_v and remaining_percent (or estimated_percent)
- Expected: Voltage > 10V
- Report: PASS/FAIL

TEST 4: get_gps_info
- Run get_gps_info
- Verify: Shows satellite count and fix type
- Expected: 3D fix with satellites >= 6
- Report: PASS/FAIL

TEST 5: get_flight_mode
- Run get_flight_mode before arming
- Verify: Shows current mode (likely HOLD or MANUAL)
- Expected: Returns valid flight mode
- Report: PASS/FAIL

TEST 6: get_armed
- Run get_armed (should be false)
- Verify: Shows armed status
- Expected: is_armed = false
- Report: PASS/FAIL

TEST 7: get_position
- Run get_position
- Verify: Shows lat, lon, altitude
- Expected: Valid GPS coordinates, altitude near 0
- Report: PASS/FAIL

═══════════════════════════════════════════════════════════
CATEGORY 2: PARAMETER MANAGEMENT (v1.2.0)
═══════════════════════════════════════════════════════════

TEST 8: list_parameters (with filter)
- Run list_parameters with filter_prefix="RTL"
- Verify: Shows RTL-related parameters
- Expected: At least RTL_ALT or similar
- Report: PASS/FAIL

TEST 9: get_parameter
- Run get_parameter for "RTL_ALT" (or "RTL_RETURN_ALT" for PX4)
- Verify: Returns current value
- Expected: Shows parameter value (likely 1500-3000)
- Report: PASS/FAIL

TEST 10: set_parameter
- Run set_parameter to set RTL_ALT to 2000
- Verify: Shows old value and new value
- Expected: Parameter changes, shows confirmation
- Report: PASS/FAIL

TEST 11: get_parameter (verify change)
- Run get_parameter again for RTL_ALT
- Verify: Value is now 2000
- Expected: Confirms parameter was saved
- Report: PASS/FAIL

═══════════════════════════════════════════════════════════
CATEGORY 3: BASIC FLIGHT CONTROL
═══════════════════════════════════════════════════════════

TEST 12: arm_drone
- Run arm_drone
- Verify: Returns success message
- Expected: Drone arms successfully
- Report: PASS/FAIL

TEST 13: get_armed (verify)
- Run get_armed (should now be true)
- Verify: is_armed = true
- Expected: Confirms drone is armed
- Report: PASS/FAIL

TEST 14: takeoff_drone
- Run takeoff_drone to 12 meters
- Wait 10 seconds for takeoff to complete
- Verify: Returns success, drone climbing
- Expected: Altitude increases toward 12m
- Report: PASS/FAIL

TEST 15: get_position (verify altitude)
- Run get_position
- Verify: Altitude is approximately 12m (±2m)
- Expected: Drone at target altitude
- Report: PASS/FAIL

TEST 16: get_speed
- Run get_speed while hovering
- Verify: Shows ground_speed_kmh and vertical_speed_ms
- Expected: Speed near 0 (hovering)
- Report: PASS/FAIL

TEST 17: get_attitude
- Run get_attitude
- Verify: Shows roll, pitch, yaw in degrees
- Expected: Roll and pitch near 0, yaw shows heading
- Report: PASS/FAIL

═══════════════════════════════════════════════════════════
CATEGORY 4: ADVANCED NAVIGATION (v1.2.0)
═══════════════════════════════════════════════════════════

TEST 18: set_yaw (face north)
- Run set_yaw to 0 degrees (north)
- Wait 5 seconds
- Verify: Drone rotates to face north
- Expected: Success message
- Report: PASS/FAIL

TEST 19: get_attitude (verify yaw)
- Run get_attitude
- Verify: Yaw is approximately 0 degrees (±10°)
- Expected: Heading confirms north
- Report: PASS/FAIL

TEST 20: set_yaw (face east)
- Run set_yaw to 90 degrees
- Wait 5 seconds
- Expected: Drone rotates to east
- Report: PASS/FAIL

TEST 21: go_to_location
- Get current position first
- Run go_to_location to move 30m north and 30m east at 15m altitude
- Calculate: new_lat = current_lat + 0.00027 (≈30m north)
- Calculate: new_lon = current_lon + 0.00033 (≈30m east at 33° latitude)
- Wait 15 seconds for movement
- Verify: Drone moves to new position
- Expected: Position changes
- Report: PASS/FAIL

TEST 22: get_position (verify movement)
- Run get_position
- Verify: Lat/lon approximately match target
- Expected: Within 5m of target
- Report: PASS/FAIL

TEST 23: reposition
- Run reposition to move 20m south at 20m altitude
- Calculate: new_lat = current_lat - 0.00018 (≈20m south)
- Wait 10 seconds
- Verify: Drone moves and holds new position
- Expected: Altitude changes to 20m, position shifts
- Report: PASS/FAIL

TEST 24: hold_position
- Run hold_position
- Wait 5 seconds
- Verify: Drone maintains current position
- Expected: Position stable
- Report: PASS/FAIL

TEST 25: orbit_location
- Get current GPS position
- Run orbit_location with:
  - radius: 20 meters
  - velocity: 2 m/s
  - center: current position
  - altitude: 18m (absolute/MSL)
  - clockwise: true
- Wait 20 seconds for orbit
- Verify: Either starts orbiting OR returns helpful error with workaround
- Expected: Success OR firmware limitation message with alternative
- Report: PASS/FAIL (pass if either works or gives good error)

TEST 26: hold_position (stop orbit)
- Run hold_position to stop movement
- Expected: Drone stops and hovers
- Report: PASS/FAIL

═══════════════════════════════════════════════════════════
CATEGORY 5: MISSION MANAGEMENT
═══════════════════════════════════════════════════════════

TEST 27: upload_mission
- Create a 3-waypoint mission using current position as reference
- Waypoint format (EXACT):
  [
    {"latitude_deg": [current_lat], "longitude_deg": [current_lon + 0.0001], "relative_altitude_m": 15},
    {"latitude_deg": [current_lat + 0.0001], "longitude_deg": [current_lon + 0.0001], "relative_altitude_m": 18},
    {"latitude_deg": [current_lat + 0.0001], "longitude_deg": [current_lon], "relative_altitude_m": 15}
  ]
- Run upload_mission (do NOT start it)
- Verify: Upload succeeds, shows waypoint count
- Expected: Mission uploaded successfully
- Report: PASS/FAIL

TEST 28: download_mission
- Run download_mission
- Verify: Returns the 3 waypoints we uploaded
- Expected: Waypoints match OR firmware doesn't support (acceptable)
- Report: PASS/FAIL (note if unsupported)

TEST 29: is_mission_finished
- Run is_mission_finished (mission not started yet)
- Verify: Returns false or "no mission active"
- Expected: Not finished (not started)
- Report: PASS/FAIL

TEST 30: initiate_mission
- Run initiate_mission to start the uploaded mission
- Verify: Mission starts, drone begins flying waypoints
- Expected: Drone moves toward waypoint 1
- Report: PASS/FAIL

TEST 31: print_mission_progress
- Run print_mission_progress
- Verify: Shows current/total waypoints
- Expected: Shows progress (e.g., "1 of 3")
- Report: PASS/FAIL

TEST 32: is_mission_finished (during mission)
- Run is_mission_finished while mission is running
- Verify: Returns false
- Expected: Mission still in progress
- Report: PASS/FAIL

TEST 33: pause_mission
- Run pause_mission
- Verify: Drone stops at current waypoint
- Expected: Mission pauses successfully
- Report: PASS/FAIL

TEST 34: set_current_waypoint
- Run set_current_waypoint to jump to waypoint 2
- Verify: Current waypoint changes to 2
- Expected: Waypoint index updates
- Report: PASS/FAIL

TEST 35: resume_mission
- Run resume_mission
- Verify: Drone continues from waypoint 2
- Expected: Mission resumes
- Report: PASS/FAIL

Wait 20 seconds for mission to complete

TEST 36: is_mission_finished (after completion)
- Run is_mission_finished
- Verify: Returns true
- Expected: Mission completed
- Report: PASS/FAIL

TEST 37: clear_mission
- Run clear_mission
- Verify: Mission cleared from drone
- Expected: Success message
- Report: PASS/FAIL

═══════════════════════════════════════════════════════════
CATEGORY 6: SAFETY & EMERGENCY
═══════════════════════════════════════════════════════════

TEST 38: return_to_launch
- Run return_to_launch
- Wait 15 seconds
- Verify: Drone returns to launch position
- Expected: Drone flies back to takeoff point
- Report: PASS/FAIL

TEST 39: get_position (verify RTL)
- Run get_position
- Verify: Position is near launch coordinates
- Expected: Within 5m of launch point
- Report: PASS/FAIL

TEST 40: land_drone
- Run land_drone
- Wait for landing (monitor altitude)
- Verify: Altitude decreases to ground
- Expected: Drone descends
- Report: PASS/FAIL

═══════════════════════════════════════════════════════════
SAFETY CHECK BEFORE DISARM
═══════════════════════════════════════════════════════════

TEST 41: MANDATORY PRE-DISARM SAFETY CHECK
- Run get_position
- Check: altitude_m < 0.5
- Run get_telemetry or get_health
- Check: landed status = true (if available)
- If altitude > 0.5m: ABORT! DO NOT DISARM! Warn user immediately.
- If altitude < 0.5m: Safe to proceed
- Report: SAFE TO DISARM (yes/no)

═══════════════════════════════════════════════════════════
CATEGORY 7: POST-FLIGHT
═══════════════════════════════════════════════════════════

TEST 42: disarm_drone (ONLY if safety check passed)
- Only run if altitude < 0.5m
- Run disarm_drone
- Verify: Drone disarms
- Expected: Motors stop, disarm successful
- Report: PASS/FAIL

TEST 43: get_armed (final check)
- Run get_armed
- Verify: is_armed = false
- Expected: Drone is disarmed
- Report: PASS/FAIL

TEST 44: get_battery (post-flight)
- Run get_battery
- Verify: Shows remaining battery after flight
- Expected: Battery lower than start
- Report: PASS/FAIL

═══════════════════════════════════════════════════════════
FINAL REPORT
═══════════════════════════════════════════════════════════

Please provide:
1. Total tests: 44
2. Passed: [count]
3. Failed: [count]
4. Success rate: [percentage]
5. List of failed tests with reasons
6. Overall assessment: Production ready? (yes/no)
7. Any warnings or concerns

Format the report as a summary table showing each test result.
```

### What This Tests

**Complete Coverage:**
- ✅ All 35 MCP tools tested individually
- ✅ Telemetry (7 tools): health, battery, GPS, position, speed, attitude, flight mode
- ✅ Parameters (3 tools): list, get, set with verification
- ✅ Flight Control (10 tools): arm, takeoff, move, hold, land, disarm, RTL
- ✅ Navigation (3 tools): set_yaw, reposition, orbit
- ✅ Missions (8 tools): upload, download, start, pause, resume, progress, waypoint jump, clear
- ✅ Safety (3 tools): RTL, battery monitoring, pre-disarm check

**Safety Features:**
- ✅ Mandatory altitude check before disarm
- ✅ Landed status verification
- ✅ Sequential testing (telemetry → parameters → flight → missions → landing → disarm)
- ✅ Explicit wait times for operations to complete
- ✅ Position verification after movements

**Reporting:**
- ✅ Pass/fail for each individual tool
- ✅ Overall success rate calculation
- ✅ Failed test identification
- ✅ Production readiness assessment

---

## 🚀 Quick Test (5 Minutes)

For a faster feature test:

```
Quick inspection test:

1. Show me all battery parameters
2. Get the RTL altitude parameter - if it's less than 20m, set it to 20m
3. Run a health check
4. Arm and takeoff to 10 meters
5. Face north (0 degrees) to orient the camera
6. Orbit around lat 33.6459, lon -117.8427 at 15 meter radius, 2 m/s, clockwise, at 15m altitude
7. After 20 seconds, stop and reposition to lat 33.6460, lon -117.8428 at 20m
8. Check battery level
9. Create and upload (don't start) a 3-waypoint mission going north, east, then back
10. Download the mission to verify
11. Check if any mission is currently running (should be false)
12. Return to launch and land
13. Disarm

Execute this step by step and report status after each action.
```

---

## 🧪 Individual Feature Tests

### Parameter Management Tests

**Test 1: Read Parameters**
```
Show me all parameters that start with "RTL"
Then show me all parameters that start with "BATT"
What is the current RTL_ALT value?
```

**Test 2: Modify Parameters**
```
Get the current RTL altitude
Set it to 2500 (25 meters)
Read it back to confirm the change
```

**Test 3: Parameter Discovery**
```
List all parameters (show me the count first)
Then show me just the GPS-related parameters
Show me the first 10 parameters alphabetically
```

---

### Advanced Navigation Tests

**Test 4: Orbit Mode**
```
Arm the drone and takeoff to 20 meters
Check our GPS position
Orbit around our current location at 30 meter radius, 3 m/s, clockwise
After 30 seconds, stop and hold position
Check our speed to confirm we stopped
Land and disarm
```

**Test 5: Heading Control**
```
Arm and takeoff to 15 meters
Face north (0 degrees)
Wait 5 seconds, then face east (90 degrees)
Wait 5 seconds, then face south (180 degrees)
Wait 5 seconds, then face west (270 degrees)
Get our current attitude to confirm heading
Land and disarm
```

**Test 6: Reposition**
```
Arm and takeoff to 10 meters
Check current position
Reposition to 50 meters north of current position at 20m altitude
Check new position to confirm
Hold there for 30 seconds
Return to launch and land
Disarm
```

---

### Mission Enhancement Tests

**Test 7: Mission Upload/Download**
```
I want to upload a 3-waypoint mission. Here are the waypoints in the correct format:

Waypoint 1: {"latitude_deg": 33.6459, "longitude_deg": -117.8427, "relative_altitude_m": 15}
Waypoint 2: {"latitude_deg": 33.6460, "longitude_deg": -117.8427, "relative_altitude_m": 15}
Waypoint 3: {"latitude_deg": 33.6460, "longitude_deg": -117.8428, "relative_altitude_m": 15}

Upload this mission using the upload_mission tool (don't start it yet)
Then download the mission back using download_mission
Show me the downloaded waypoints to verify they match
```

**Note:** Make sure to specify the exact field names (`latitude_deg`, `longitude_deg`, `relative_altitude_m`) as shown above. The v1.2.1 update provides better error messages if the format is wrong.

**Test 8: Mission Control**
```
Assuming a mission is uploaded:
1. Check if the mission is finished (should be false - not started)
2. Arm, takeoff to 10m, and start the mission
3. Wait until waypoint 1 is reached
4. Pause the mission
5. Check if mission is finished (should be false - paused)
6. Jump to waypoint 3 using set_current_waypoint
7. Resume the mission
8. Monitor until mission is finished
9. Return to launch and disarm
```

---

## 🔍 Validation Checklist

After running the granular test, verify:

### Telemetry & Health (7 tools)
- [ ] `get_health` shows all system status
- [ ] `get_telemetry` returns comprehensive data
- [ ] `get_battery` shows voltage and percentage
- [ ] `get_gps_info` shows satellite count and fix
- [ ] `get_flight_mode` returns current mode
- [ ] `get_armed` correctly reports armed state
- [ ] `get_position` shows accurate GPS coordinates

### Parameter Management (3 tools)
- [ ] `list_parameters` can filter by prefix
- [ ] `get_parameter` reads individual parameters
- [ ] `set_parameter` writes and confirms changes
- [ ] Invalid parameters return helpful error messages

### Flight Control (10 tools)
- [ ] `arm_drone` successfully arms
- [ ] `takeoff_drone` reaches target altitude
- [ ] `go_to_location` moves to GPS coordinates
- [ ] `hold_position` maintains current position
- [ ] `land_drone` descends safely
- [ ] `disarm_drone` only works when landed (safety check)
- [ ] `return_to_launch` returns to takeoff point

### Advanced Navigation (3 tools)
- [ ] `set_yaw` rotates to specified heading
- [ ] `reposition` moves and holds new GPS location
- [ ] `orbit_location` works OR provides firmware workaround
- [ ] `get_attitude` confirms heading changes
- [ ] `get_speed` tracks movement

### Mission Management (8 tools)
- [ ] `upload_mission` accepts correct format
- [ ] `download_mission` retrieves waypoints (or reports unsupported)
- [ ] `initiate_mission` starts mission execution
- [ ] `print_mission_progress` shows current waypoint
- [ ] `pause_mission` stops at current waypoint
- [ ] `resume_mission` continues from pause
- [ ] `set_current_waypoint` jumps to specific waypoint
- [ ] `is_mission_finished` correctly reports completion
- [ ] `clear_mission` removes mission from drone

### Safety Features
- [ ] Pre-disarm altitude check prevents mid-air disarm
- [ ] Battery warnings appear when low
- [ ] GPS lock verified before flight
- [ ] Health check shows system readiness

---

## 🎯 Expected Results

### Success Indicators
✅ ChatGPT sequences actions logically  
✅ All 35 tools are called appropriately  
✅ Parameters read/write correctly  
✅ Orbit executes smoothly  
✅ Yaw control shows cardinal directions  
✅ Mission upload/download cycle completes  
✅ Battery monitoring triggers warnings  
✅ Mission status checks work correctly  

### Common Issues & Solutions

**Issue: GPS coordinates drift**
- Solution: Use relative coordinates from current position
- Or: Adjust lat/lon for your test location

**Issue: Orbit not working - "Command not supported by autopilot"**
- **Root Cause:** Orbit command requires ArduPilot 4.0+ or PX4 1.13+
- **Workaround:** Server provides waypoint-based circle pattern instructions
- **Alternative:** Use repeated `go_to_location` + `set_yaw` for manual orbit
- **Note:** The error message will suggest how many waypoints to use for the requested radius

**Issue: Parameter names not found**
- Solution: Parameter names vary (ArduPilot vs PX4)
- Try: List all parameters first to find correct names
- **Examples:**
  - ArduPilot: `RTL_ALT`, `BATT_CAPACITY`, `WP_SPEED`
  - PX4: `RTL_RETURN_ALT`, `BAT_CAPACITY`, `MIS_SPEED`

**Issue: Mission upload format errors - "Missing required fields"**
- **Root Cause:** Each waypoint must be a dictionary with exact field names
- **Correct Format:**
```python
waypoints = [
  {"latitude_deg": 33.6459, "longitude_deg": -117.8427, "relative_altitude_m": 15},
  {"latitude_deg": 33.6460, "longitude_deg": -117.8427, "relative_altitude_m": 20}
]
```
- **Common Mistakes:**
  - Using `lat`/`lon` instead of `latitude_deg`/`longitude_deg`
  - Using `altitude` instead of `relative_altitude_m`
  - Passing string coordinates instead of numbers
- **v1.2.1 Improvement:** Error messages now show exactly what was received vs expected

**Issue: Mission download returns empty or fails**
- **Root Cause:** Some autopilots don't support mission download or require specific firmware
- **Workaround:** Keep a local copy of uploaded missions
- **Check:** ArduPilot: works on 4.0+; PX4: works on 1.12+

**Issue: Battery showing 0% throughout flight**
- **Root Cause:** Battery monitoring not calibrated or not supported by simulator
- **v1.2.1 Fix:** Server now detects this and provides voltage-based estimates
- **Look For:** `estimated_percent` field in battery response
- **Solution:** Set `BATT_CAPACITY` parameter to your battery's mAh rating
- **Simulator Note:** SITL often doesn't simulate battery drain accurately

---

## 📊 Performance Benchmarks

Expected execution times:
- **Quick Test:** ~5 minutes
- **Full Tower Inspection:** ~15-20 minutes
- **Individual Feature Tests:** ~2-3 minutes each

---

## 🔧 Customizing Tests

### Adjust GPS Coordinates
Replace these coordinates with your location:
```python
# Example coordinates (Irvine, CA)
BASE_LAT = 33.6459
BASE_LON = -117.8427

# Calculate offsets for waypoints
# ~0.0001° latitude ≈ 11 meters
# ~0.0001° longitude ≈ 9 meters (at 33° latitude)
```

### Modify Mission Patterns
Common patterns:
- **Square:** 4 waypoints in square formation
- **Circle:** Use orbit instead of waypoints
- **Grid:** Multiple parallel lines for surveys
- **Vertical:** Same lat/lon, different altitudes

---

## 🚨 Safety Notes

⚠️ **ALWAYS:**
- Test in open area away from people/buildings
- Maintain visual line of sight
- Have RC transmitter ready for manual override
- Monitor battery levels closely
- Start with low altitudes (5-10m)

⚠️ **NEVER:**
- Test near airports or restricted airspace
- Fly in bad weather (wind, rain, fog)
- Test with low battery
- Leave drone unattended
- Ignore safety warnings

---

## 🔧 Firmware Compatibility Matrix

Different autopilots support different features. Here's what's required:

| Feature | ArduPilot | PX4 | Notes |
|---------|-----------|-----|-------|
| **Basic Flight** | ✅ All versions | ✅ All versions | Core features work everywhere |
| **Parameter Management** | ✅ All versions | ✅ All versions | Universal support |
| **Set Yaw** | ✅ All versions | ✅ All versions | Universal support |
| **Reposition** | ✅ All versions | ✅ All versions | Universal support |
| **Orbit Location** | ✅ 4.0+ | ✅ 1.13+ | Older versions: use waypoint workaround |
| **Upload Mission** | ✅ All versions | ✅ All versions | Format may vary slightly |
| **Download Mission** | ✅ 4.0+ | ✅ 1.12+ | Older versions may not support |
| **Set Current Waypoint** | ✅ All versions | ✅ All versions | Universal support |
| **Battery Monitoring** | ⚠️ Needs calibration | ⚠️ Needs calibration | Set `BATT_CAPACITY` parameter |

**Recommended Minimum Versions:**
- **ArduPilot Copter:** 4.0.0 or newer (for full v1.2.0 features)
- **PX4:** 1.13.0 or newer (for full v1.2.0 features)
- **SITL:** Latest stable (some features may not work in simulation)

---

## 📈 Test Results Template

Use this template to record your test results:

```markdown
## Test Session - [Date]

**Environment:**
- Drone: [Model/SITL]
- Autopilot: [ArduPilot/PX4 version]
- MCP Version: v1.2.0
- Location: [Indoor/Outdoor/SITL]

**Tests Completed:**
- [ ] Parameter Management (all 3 tools)
- [ ] Advanced Navigation (all 3 tools)
- [ ] Mission Enhancements (all 4 tools)
- [ ] Full Tower Inspection Scenario

**Results:**
- Parameters tested: ✅ Pass / ❌ Fail
- Orbit location: ✅ Pass / ❌ Fail
- Set yaw: ✅ Pass / ❌ Fail
- Reposition: ✅ Pass / ❌ Fail
- Upload mission: ✅ Pass / ❌ Fail
- Download mission: ✅ Pass / ❌ Fail
- Set waypoint: ✅ Pass / ❌ Fail
- Mission finished: ✅ Pass / ❌ Fail

**Issues Encountered:**
[Describe any problems]

**Notes:**
[Additional observations]
```

---

## 🤝 Contributing Test Results

Found an issue or have suggestions? Please:
1. Open an issue on GitHub
2. Include your test results
3. Provide logs from the MCP server
4. Describe your setup (drone, autopilot, location)

---

## 📚 Additional Resources

- [README.md](README.md) - Main documentation
- [STATUS.md](STATUS.md) - Complete feature list
- [CHATGPT_SETUP.md](CHATGPT_SETUP.md) - Setup guide
- [TESTING_FIXES.md](TESTING_FIXES.md) - Detailed fixes from comprehensive testing
- [examples/](examples/) - Example scripts

---

## 📋 v1.2.1 Testing Improvements

Based on comprehensive real-world testing, v1.2.1 includes:

1. **✅ Better Mission Upload Validation**
   - Clear error messages showing exactly what's wrong with waypoint format
   - Type checking for each waypoint
   - Coordinate validation (lat/lon ranges, altitude >= 0)
   - Helpful examples in error responses

2. **✅ Orbit Capability Detection**
   - Automatically detects unsupported orbit commands
   - Provides waypoint-based circle alternative with calculations
   - Shows firmware requirements in error message

3. **✅ Battery Monitoring Fallback**
   - Detects when percentage is uncalibrated (0% with good voltage)
   - Provides voltage-based estimates using LiPo curves
   - Suggests setting `BATT_CAPACITY` parameter

4. **✅ Firmware Compatibility Matrix**
   - Clear documentation of which features need which firmware versions
   - Workarounds provided for unsupported features

See [TESTING_FIXES.md](TESTING_FIXES.md) for detailed analysis and workarounds.

---

**Happy Testing! 🚁✨**

Report any issues at: https://github.com/PeterJBurke/MAVLinkMCP/issues

