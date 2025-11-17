# Upload/Download Mission Diagnostic Test

Quick test to verify the mission upload/download fix is working.

## Prerequisites

1. Server must be updated to latest code (with vehicle_action fix)
2. Drone must be connected and GPS locked
3. Drone should be on the ground (don't need to fly for this test)

---

## Test Prompt for ChatGPT

```
I need to test mission upload and download. Please do exactly these steps:

STEP 1: Check current mission status
- Run is_mission_finished to see current state

STEP 2: Clear any existing mission
- Run clear_mission to start fresh

STEP 3: Upload a simple 2-waypoint mission (DO NOT START IT)
Use upload_mission with these exact waypoints:
[
  {"latitude_deg": 33.6459, "longitude_deg": -117.8427, "relative_altitude_m": 10},
  {"latitude_deg": 33.6460, "longitude_deg": -117.8428, "relative_altitude_m": 15}
]

STEP 4: Download the mission immediately after upload
- Run download_mission
- Verify the waypoints match what was uploaded

STEP 5: Report results
Tell me:
- Did upload_mission succeed? (status, any errors)
- Did download_mission succeed? (status, any errors)
- Do the downloaded waypoints match the uploaded waypoints?
- If there were errors, what were the EXACT error messages?

CRITICAL: 
- Use upload_mission (NOT initiate_mission) for step 3
- Download BEFORE starting any mission
- Report EXACT error messages if anything fails
```

---

## Expected Results

### ✅ If Server is Updated (vehicle_action fix applied):

**Step 3 - upload_mission:**
```json
{
  "status": "success",
  "message": "Mission uploaded with 2 waypoints",
  "waypoint_count": 2
}
```

**Step 4 - download_mission:**
```json
{
  "status": "success",
  "waypoint_count": 2,
  "waypoints": [
    {"latitude_deg": 33.6459, "longitude_deg": -117.8427, "relative_altitude_m": 10},
    {"latitude_deg": 33.6460, "longitude_deg": -117.8428, "relative_altitude_m": 15}
  ]
}
```

---

### ❌ If Server NOT Updated (still has vehicle_action bug):

**Step 3 - upload_mission:**
```json
{
  "status": "failed",
  "error": "MissionItem.__init__() missing 1 required positional argument: 'vehicle_action'"
}
```

**Step 4 - download_mission:**
```json
{
  "status": "failed",
  "error": "Mission download failed - no mission available or mission was cleared"
}
```

---

## Troubleshooting

### If upload_mission still fails with 'vehicle_action' error:

**Server not updated yet!** Run on your server:
```bash
cd ~/MAVLinkMCP
git pull origin main
uv sync
sudo systemctl restart mavlinkmcp
sudo systemctl status mavlinkmcp
```

### If download_mission fails with "UNSUPPORTED":

**Possible causes:**
1. Mission was never uploaded (upload_mission failed first)
2. Mission was cleared before download
3. Firmware limitation (less likely - ArduPilot supports this)

**Check the server logs:**
```bash
sudo journalctl -u mavlinkmcp -n 50 | grep -E "upload_mission|download_mission"
```

### If upload works but download says "no mission available":

This means the upload didn't actually work or was cleared. Check:
```bash
sudo journalctl -u mavlinkmcp -n 50 | grep "Mission upload"
```

---

## What This Tests

- ✅ `upload_mission` with the vehicle_action fix
- ✅ `download_mission` immediately after upload
- ✅ Mission persistence (upload → download cycle)
- ✅ Waypoint data integrity

---

## Next Steps

**If test passes:** 
- ✅ Mission upload/download is working
- ✅ You can use these tools in real tests
- ✅ The TESTING_QUICK.md should now work for steps 9-10

**If test fails:**
- ❌ Server needs updating (see troubleshooting above)
- ❌ Or there's a deeper firmware issue (check ArduPilot version)

---

[← Back to Testing Guide](TESTING_GUIDE.md)

