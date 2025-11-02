# MAVLink MCP Server

A Python-based Model Context Protocol (MCP) server for AI-powered drone control. Connect LLMs to MAVLink-enabled drones (PX4, ArduPilot) for natural language flight control.

## Features

- 🤖 **AI-Powered Control**: Use natural language to command drones via GPT-4, Claude, or other LLMs
- 🚁 **MAVLink Compatible**: Works with PX4, ArduPilot, and other MAVLink drones
- 🔧 **MCP Protocol**: Standard Model Context Protocol for tool integration
- 📡 **Network/Serial Support**: Connect via UDP, TCP, or serial ports
- 🛡️ **Safe Configuration**: Secure handling of connection credentials

## Prerequisites

- **Python 3.12+** (comes with Ubuntu 24.04)
- **Ubuntu 24.04** cloud instance or server
- **uv** package manager ([install here](https://github.com/astral-sh/uv))
- **MAVLink-compatible drone or simulator** with network access (IP address and port)
  - Connection details will be configured in `.env` file
- **OpenAI or Anthropic API key** (for AI agent control)

## Quick Start

### 1. Set Up Your System

**If starting from a fresh Ubuntu 24.04 instance** (AWS, Digital Ocean, Linode, etc.):

```bash
# Update package list
sudo apt update

# Upgrade packages (non-interactive, no prompts)
sudo DEBIAN_FRONTEND=noninteractive apt upgrade -y -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold"

# Install essential dependencies
sudo apt install -y python3 python3-pip python3-venv git curl build-essential

# Verify Python version (Ubuntu 24.04 comes with Python 3.12)
python3 --version
```

**Expected output:** `Python 3.12.x`

**Install uv package manager:**

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Restart your shell or load the environment:**

```bash
source $HOME/.bashrc
# Or if using zsh: source $HOME/.zshrc
```

**Verify uv installation:**

```bash
uv --version
```

### 2. Clone and Install

```bash
git clone https://github.com/PeterJBurke/MAVLinkMCP.git
cd MAVLinkMCP

# Install all dependencies
uv sync

# If you get module import errors, try removing the lock file and reinstalling
# rm uv.lock
# uv sync --upgrade
```

### 3. Configure Connection and API Keys

**a) Set up drone connection:**

Copy the example configuration:
```bash
cp .env.example .env
```

Edit `.env` with your drone's IP and port:
```bash
nano .env
```

Set your drone's connection details:
```bash
MAVLINK_ADDRESS=<your-drone-ip>
MAVLINK_PORT=14540  # Or your drone's specific port
```

**Save and exit:** Press `Ctrl+X`, then `Y`, then `Enter`

**b) Add your API key:**

Create the secrets file:
```bash
nano examples/fastagent.secrets.yaml
```

Add your OpenAI or Anthropic API key:
```yaml
openai:
    api_key: sk-your-actual-openai-key-here
```

Or for Claude:
```yaml
anthropic:
    api_key: sk-ant-your-anthropic-key-here
```

**Save and exit:** Press `Ctrl+X`, then `Y`, then `Enter`

### 4. Test the Setup

```bash
# Test the example (shows available commands)
uv run examples/example_agent.py

# Or run the MCP server directly for testing
uv run src/server/mavlinkmcp.py
```

**Note:** The MCP server connects to your drone and exposes control tools. You can integrate it with AI agents or call the tools programmatically.

**Available drone control functions:**
- `arm_drone()` - Arm the motors
- `takeoff(altitude)` - Take off to specified altitude
- `get_position()` - Get GPS position
- `move_to_relative(lr, fb, altitude, yaw)` - Move relative to current position  
- `land()` - Land the drone
- `get_flight_mode()` - Get current flight mode

## Usage

### Running the MCP Server

The MAVLink MCP server exposes drone control as MCP tools that can be used by AI agents or other MCP clients:

```bash
# Run the MCP server (connects to your drone via .env settings)
uv run src/server/mavlinkmcp.py
```

The server will:
1. Load drone connection settings from `.env`
2. Connect to your drone at the specified IP and port
3. Wait for GPS lock
4. Expose drone control tools via the MCP protocol

### Integrating with AI Agents

The MCP server can be integrated with various AI frameworks:

- **MCP-compatible AI agents** - Connect any MCP client to the server
- **Custom Python clients** - Use the `mcp-agent` package to build custom integrations
- **LLM applications** - Expose drone control as tools/functions to LLMs

**Note:** The `mcp-agent` package API has changed significantly. We're working on updated examples for the new API. For now, you can run the server directly and integrate it with your preferred MCP client.

### Quick Launch Scripts

Test connection:
```bash
./test_connection.sh
```

Start agent with auto-configuration:
```bash
./start_agent.sh
```

## Documentation

- **[Deployment Guide](DEPLOYMENT_GUIDE.md)** - Complete setup and usage instructions
- **[Examples README](examples/README.md)** - Example agent documentation
- **[MCP Protocol](https://modelcontextprotocol.io/)** - Model Context Protocol docs
- **[MAVSDK](https://mavsdk.mavlink.io/)** - MAVLink SDK documentation

## Available Tools

The MCP server exposes these tools for drone control:

| Category | Tools |
|----------|-------|
| **Flight Control** | `arm_drone`, `takeoff`, `land`, `move_to_relative` |
| **Telemetry** | `get_position`, `get_flight_mode`, `get_imu`, `print_status_text` |
| **Missions** | `initiate_mission`, `print_mission_progress` |

## Configuration

Create a `.env` file in the project root:

```bash
# Drone connection details
MAVLINK_ADDRESS=<your-drone-ip>  # Your drone IP address
MAVLINK_PORT=14540               # MAVLink port (default: 14540)
```

For the AI agent, create `examples/fastagent.secrets.yaml`:

```yaml
openai:
    api_key: sk-your-key-here
```

## Safety Guidelines

⚠️ **IMPORTANT**: Always follow drone safety protocols:

- Maintain visual line of sight
- Verify GPS lock before flight
- Have manual RC override ready
- Test in open areas away from people
- Check local regulations and weather
- Start with low altitudes (3-5m)

## Development

This project uses `uv` for dependency management:

```bash
# Install dependencies
uv sync

# Run the server
uv run src/server/mavlinkmcp.py

# Run the example agent
uv run examples/example_agent.py

# Add a new dependency
uv add package-name
```

## Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Acknowledgments

- Original project by [Ion Gabriel](https://github.com/ion-g-ion/MAVLinkMCP)
- Built with [MAVSDK](https://mavsdk.mavlink.io/)
- Uses [Model Context Protocol](https://modelcontextprotocol.io/)

## Getting API Keys

### OpenAI API Key (for GPT-4o-mini, GPT-4o, etc.)

1. **Create an OpenAI account:**
   - Go to [https://platform.openai.com/signup](https://platform.openai.com/signup)
   - Sign up with your email or Google/Microsoft account

2. **Add billing information:**
   - Navigate to [https://platform.openai.com/account/billing](https://platform.openai.com/account/billing)
   - Add a payment method (required for API access)
   - Consider setting usage limits to control costs

3. **Create an API key:**
   - Go to [https://platform.openai.com/api-keys](https://platform.openai.com/api-keys)
   - Click **"Create new secret key"**
   - Give it a name (e.g., "MAVLink MCP")
   - **Copy the key immediately** - you won't be able to see it again!
   - Key format: `sk-proj-...` or `sk-...`

4. **Add to your project:**
   ```bash
   nano examples/fastagent.secrets.yaml
   ```
   ```yaml
   openai:
       api_key: sk-proj-your-actual-key-here
   ```

**Pricing:** Pay-as-you-go. GPT-4o-mini costs ~$0.15 per 1M input tokens. Check current pricing at [https://openai.com/api/pricing/](https://openai.com/api/pricing/)

### Anthropic API Key (for Claude)

1. **Create an Anthropic account:**
   - Go to [https://console.anthropic.com/](https://console.anthropic.com/)
   - Sign up with your email

2. **Add billing:**
   - Navigate to **Settings → Billing**
   - Add a payment method
   - Purchase credits (minimum $5)

3. **Create an API key:**
   - Go to **Settings → API Keys**
   - Click **"Create Key"**
   - Give it a name (e.g., "MAVLink MCP")
   - **Copy the key immediately** - you won't be able to see it again!
   - Key format: `sk-ant-...`

4. **Add to your project:**
   ```bash
   nano examples/fastagent.secrets.yaml
   ```
   ```yaml
   anthropic:
       api_key: sk-ant-your-actual-key-here
   ```

**Pricing:** Prepaid credits. Claude 3.5 Sonnet costs ~$3 per 1M input tokens. Check current pricing at [https://www.anthropic.com/pricing](https://www.anthropic.com/pricing)

### Security Notes

- **Never commit API keys to Git** - the `.gitignore` is configured to protect `fastagent.secrets.yaml`
- **Keep keys private** - treat them like passwords
- **Set spending limits** - both platforms allow budget controls
- **Rotate keys regularly** - especially if you suspect they've been exposed
- **Use separate keys** - for development vs production

## Troubleshooting

### ModuleNotFoundError: No module named 'mcp_agent'

If you see this error when running the agent:
```
ModuleNotFoundError: No module named 'mcp_agent.core.fastagent'
```

**Solution 1 - Get the latest code with the fix:**
```bash
cd MAVLinkMCP

# Pull the latest code with updated imports
git pull origin main

# Reinstall dependencies
uv sync

# Try again
uv run examples/example_agent.py
```

**Solution 2 - If you still have issues:**
```bash
cd MAVLinkMCP

# Remove the lock file
rm uv.lock

# Reinstall with latest versions
uv sync --upgrade

# Verify installation
uv run python -c "import mcp_agent; print('mcp_agent installed successfully')"
```

### Warning about deprecated dev-dependencies

If you see:
```
warning: The `tool.uv.dev-dependencies` field is deprecated
```

This warning is harmless but to fix it, run:
```bash
git pull origin main  # Get latest pyproject.toml with the fix
uv sync
```

### Connection to drone fails

1. **Check drone is reachable:**
   ```bash
   ping <your-drone-ip>
   ```

2. **Verify .env file:**
   ```bash
   cat .env
   # Should show your drone's IP and port
   ```

3. **Check port accessibility:**
   ```bash
   nc -zv <your-drone-ip> <port>
   ```

4. **Verify environment variables:**
   ```bash
   uv run python -c "import os; print(os.getenv('MAVLINK_ADDRESS'), os.getenv('MAVLINK_PORT'))"
   ```

### API Key not working

1. **Verify secrets file exists:**
   ```bash
   ls -la examples/fastagent.secrets.yaml
   ```

2. **Check file contents:**
   ```bash
   cat examples/fastagent.secrets.yaml
   # Should show your API key (keep it private!)
   ```

3. **Verify proper YAML formatting:**
   - Use spaces, not tabs for indentation
   - Ensure proper key structure as shown in the guide

## Support

- 📖 [Full Deployment Guide](DEPLOYMENT_GUIDE.md)
- 🐛 [Report Issues](https://github.com/PeterJBurke/MAVLinkMCP/issues)
- 💬 [Discussions](https://github.com/PeterJBurke/MAVLinkMCP/discussions)
