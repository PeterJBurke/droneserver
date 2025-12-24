# Connecting LM Studio to MAVLink MCP Server

Complete guide to control your drone using natural language through LM Studio.

---

## Prerequisites

✅ **You must have:**
1. LM Studio installed ([Download here](https://lmstudio.ai/))
2. A local LLM model downloaded in LM Studio
3. The MAVLink MCP server running and exposed via ngrok
4. The ngrok URL from your `.env` file (see `NGROK_URL` variable)

---

## Server URL

Your MCP server SSE endpoint (from `.env`):

```
https://YOUR_NGROK_URL.ngrok-free.app/sse
```

⚠️ **Note:** Get the actual URL from your `.env` file (`NGROK_URL` variable). Do not share this URL publicly.

---

## Step 1: Open LM Studio

1. Launch **LM Studio** on your computer
2. Ensure you have a model loaded (e.g., Llama, Mistral, Qwen, etc.)

---

## Step 2: Configure MCP Server Connection

### A. Open Settings

1. Click the **Settings** icon (gear) in the left sidebar
2. Navigate to **"MCP Servers"** or **"Tools"** section

### B. Add New MCP Server

1. Click **"Add Server"** or **"+"** button
2. Enter the following configuration:

| Field | Value |
|-------|-------|
| **Name** | `droneserver` |
| **Type** | `SSE` (Server-Sent Events) |
| **URL** | `https://YOUR_NGROK_URL.ngrok-free.app/sse` |

⚠️ Replace `YOUR_NGROK_URL` with the actual value from your `.env` file.

### C. Save Configuration

1. Click **Save** or **Add**
2. The server should show as **Connected** ✅

---

## Step 3: Verify Connection

Once connected, LM Studio should display the available drone control tools:

- `get_telemetry` - Get current drone position and status
- `arm` - Arm the drone motors
- `disarm` - Disarm the drone motors
- `takeoff` - Take off to specified altitude
- `land` - Land the drone
- `goto_position` - Fly to GPS coordinates
- `set_flight_mode` - Change flight mode
- And more...

---

## Step 4: Start Chatting!

Open a new chat and try these example prompts:

### Check Drone Status
```
Check if the drone is connected and show me its current position
```

### Arm and Takeoff
```
Arm the drone and take off to 10 meters
```

### Get Telemetry
```
What's the drone's current altitude and battery level?
```

### Land
```
Land the drone safely
```

---

## Troubleshooting

### Connection Failed

1. **Verify the URL is correct** - Check your `.env` file for the `NGROK_URL` value:
   ```
   https://YOUR_NGROK_URL.ngrok-free.app/sse
   ```

2. **Check internet connection** - LM Studio needs network access to reach the ngrok URL

3. **Verify server is running** - The MCP server must be active on the remote machine

### Tools Not Appearing

1. **Restart LM Studio** after adding the MCP server
2. **Start a new chat** - Tools may not appear in existing conversations
3. **Check connection status** in MCP settings

### Commands Not Executing

1. **Ensure the drone is connected** to the MCP server
2. **Check server logs** for error messages
3. **Verify GPS lock** - Many commands require GPS

---

## Notes

- The ngrok URL may change if the server restarts. Check with your server administrator for the current URL.
- Keep the MCP server toggle **enabled** in LM Studio settings for the tools to be available.
- Some LLM models work better with tool calling than others. Models with function calling support (like Qwen, Mistral, or Llama 3.1+) are recommended.

---

## Support

- 📖 [Main README](README.md)
- 📊 [Status & Roadmap](STATUS.md)
- 🐛 [Report Issues](https://github.com/PeterJBurke/MAVLinkMCP/issues)

---

**Happy Flying with LM Studio! 🚁🤖**

