# MAVLink MCP Testing Protocol

Comprehensive testing suite for the MAVLink MCP server, providing both automated unit tests and natural language integration tests for ChatGPT/LLM control.

## 📋 Overview

The MAVLink MCP testing protocol consists of two complementary testing approaches:

| Type | Method | Duration | Best For |
|------|--------|----------|----------|
| **Unit Tests** | pytest + mocks | ~1 min | CI/CD, code changes, regression |
| **Integration Tests** | ChatGPT natural language | 5-45 min | Real drone/SITL validation |

---

## 🧪 Unit Tests (pytest)

Automated tests using pytest with mocked MAVSDK components.

### Test Files

| File | Coverage | Tests |
|------|----------|-------|
| `test_basic_flight.py` | arm, disarm, takeoff, land, hold_position | 15 |
| `test_mission.py` | Mission upload/download/control/pause/resume | 28 |
| `test_navigation.py` | go_to_location, reposition, set_yaw | 12 |
| `test_parameters.py` | list/get/set parameters | 10 |
| `test_telemetry.py` | position, battery, GPS, attitude, speed | 14 |
| `test_emergency_safety.py` | RTL, kill_switch, emergency procedures | 8 |

### Running Unit Tests

```bash
# Run all tests
uv run pytest

# Run with verbose output
uv run pytest -v

# Run specific test file
uv run pytest tests/test_basic_flight.py

# Run specific test class
uv run pytest tests/test_mission.py::TestUploadMission

# Run specific test
uv run pytest tests/test_mission.py::TestUploadMission::test_upload_mission_success

# Run with coverage
uv run pytest --cov=src/server --cov-report=html

# Run tests matching a pattern
uv run pytest -k "mission"
```

### Test Fixtures

The `conftest.py` provides reusable fixtures:

```python
# Core fixtures
mock_drone          # Fully mocked MAVSDK drone
mock_context        # MCP context with mocked connector
mock_connector      # MAVLinkConnector with mocked drone

# Specialized drones
low_battery_drone   # Battery at 15%
poor_gps_drone      # 3 satellites, 2D fix
unhealthy_drone     # Failed health checks
grounded_drone      # On ground, disarmed
mission_complete_drone  # Completed mission

# Environment
disconnected_context    # Simulates connection timeout
```

### Writing New Tests

```python
import pytest
from mavlinkmcp import your_tool

class TestYourTool:
    """Tests for your_tool function"""
    
    async def test_success_case(self, mock_context, mock_drone):
        """Test successful execution"""
        result = await your_tool(mock_context)
        
        assert result["status"] == "success"
        mock_drone.action.some_method.assert_called_once()
    
    async def test_connection_timeout(self, disconnected_context):
        """Test timeout handling"""
        result = await your_tool(disconnected_context)
        
        assert result["status"] == "failed"
        assert "timeout" in result["error"].lower()
```

---

## 🚁 Integration Tests (ChatGPT/LLM)

Natural language tests for validating real drone or SITL behavior.

### Test Suites

| Test | Duration | Complexity | Tools Tested |
|------|----------|------------|--------------|
| [Quick Test](../TESTING_QUICK.md) | 5 min | Low | 15/36 |
| [Comprehensive Test](../TESTING_COMPREHENSIVE.md) | 20 min | Medium | 35/36 |
| [Granular Test](../TESTING_GRANULAR.md) | 45 min | High | 44 tests |
| [Individual Tests](../TESTING_INDIVIDUAL.md) | 2-3 min each | Low-Med | Varies |
| [Upload/Download Diagnostic](../TESTING_UPLOAD_DOWNLOAD.md) | 5 min | Low | 4 tools |

### Quick Reference

#### Quick Test (5 minutes)
```
Copy the prompt from TESTING_QUICK.md into ChatGPT.
Tests: Parameters, navigation, basic flight, mission upload/download.
```

#### Comprehensive Test (20 minutes)
```
Copy the prompt from TESTING_COMPREHENSIVE.md into ChatGPT.
Tests: 7-phase tower inspection scenario covering all 36 tools.
```

#### Granular Test (45 minutes)
```
Copy the prompt from TESTING_GRANULAR.md into ChatGPT.
Tests: 44 individual tests with ACK/NACK verification.
```

### ACK/NACK Verification

The granular test uses intelligent verification:

- **ACK** = Tool executed AND drone performed the action (verified)
- **NACK** = Tool call succeeded BUT drone didn't act as expected
- **SKIPPED** = Prerequisites not met

Example verification:
```
TEST: set_yaw to 90 degrees
- Execute set_yaw(90)
- Wait 8 seconds
- Run get_attitude
- VERIFY: Yaw between 75° and 105° (±15° tolerance)
- ACK if verified, NACK if yaw unchanged
```

---

## 🛡️ Safety Testing

### Critical Safety Features Tested

| Feature | Unit Test | Integration Test |
|---------|-----------|------------------|
| Pre-arm checks | ✅ | ✅ |
| Pre-disarm safety | ✅ | ✅ (TEST 41) |
| Battery monitoring | ✅ | ✅ |
| GPS validation | ✅ | ✅ |
| RTL functionality | ✅ | ✅ |
| hold_mission_position (GUIDED mode) | ✅ | ✅ |

### 🔴 CRITICAL: pause_mission Deprecated

```python
# ❌ NEVER use pause_mission - enters unsafe LOITER mode
result = await pause_mission(ctx)  # Returns deprecation error

# ✅ ALWAYS use hold_mission_position - safe GUIDED mode
result = await hold_mission_position(ctx)  # Safe altitude hold
```

See [LOITER_MODE_CRASH_REPORT.md](../LOITER_MODE_CRASH_REPORT.md) for why LOITER mode is unsafe.

---

## 📊 Test Coverage

### Tool Coverage Matrix

| Category | Tools | Unit Tests | Integration |
|----------|-------|------------|-------------|
| **Telemetry** | 7 | ✅ All | ✅ All |
| **Parameters** | 3 | ✅ All | ✅ All |
| **Basic Flight** | 10 | ✅ All | ✅ All |
| **Navigation** | 3 | ✅ All | ✅ All |
| **Missions** | 10 | ✅ All | ✅ All |
| **Safety** | 3 | ✅ All | ✅ All |
| **Total** | **36** | **36/36** | **35/36** |

### Feature Coverage by Version

| Version | Features | Tested |
|---------|----------|--------|
| v1.2.0 | Parameter management | ✅ |
| v1.2.0 | Advanced navigation (yaw, reposition) | ✅ |
| v1.2.0 | Mission upload/download | ✅ |
| v1.2.2 | hold_mission_position (GUIDED mode) | ✅ |
| v1.2.2 | Enhanced resume_mission | ✅ |
| v1.2.2 | Enhanced is_mission_finished | ✅ |
| v1.2.3 | pause_mission deprecated | ✅ |
| v1.2.3 | Flight logging | ✅ |

---

## 🔧 Configuration

### Environment Variables

```bash
# Required for tests
MAVLINK_ADDRESS=127.0.0.1
MAVLINK_PORT=14540
MAVLINK_PROTOCOL=udp
```

### pytest Configuration

Add to `pyproject.toml`:

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
python_files = "test_*.py"
python_classes = "Test*"
python_functions = "test_*"
```

---

## 🚀 CI/CD Integration

### GitHub Actions Example

```yaml
name: Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Install uv
        uses: astral-sh/setup-uv@v4
      
      - name: Install dependencies
        run: uv sync
      
      - name: Run tests
        run: uv run pytest -v
      
      - name: Upload coverage
        uses: codecov/codecov-action@v4
```

---

## 📝 Test Results Template

After running tests, document results:

```markdown
## Test Session - [Date]

**Environment:**
- Drone: [Model/SITL]
- Autopilot: [ArduPilot/PX4 version]
- MCP Version: v1.2.3

**Unit Tests:**
- Total: XX passed, XX failed
- Coverage: XX%

**Integration Tests:**
- Quick Test: ✅/❌ (X/14 steps)
- Comprehensive: ✅/❌ (X/7 phases)
- Granular: XX ACK / XX NACK / XX SKIPPED

**Issues Found:**
- [Description of any issues]

**Notes:**
- [Additional observations]
```

---

## 🤝 Contributing

### Adding New Tests

1. Create test file in `tests/` directory
2. Follow naming convention: `test_<feature>.py`
3. Use fixtures from `conftest.py`
4. Test both success and failure cases
5. Include connection timeout tests

### Test Requirements

- [ ] All async functions properly awaited
- [ ] Mock drone actions verified with `assert_called_once()`
- [ ] Connection timeout case tested
- [ ] Exception handling tested
- [ ] Status and error messages validated

---

## 📚 Additional Resources

- [TESTING_GUIDE.md](../TESTING_GUIDE.md) - Main testing overview
- [TESTING_REFERENCE.md](../TESTING_REFERENCE.md) - Troubleshooting guide
- [STATUS.md](../STATUS.md) - Feature status and version history
- [FLIGHT_LOGS.md](../FLIGHT_LOGS.md) - Flight logging documentation

---

## 🔍 Troubleshooting

### Common Test Failures

**"Module not found" errors:**
```bash
# Ensure src is in Python path
export PYTHONPATH="${PYTHONPATH}:./src"
# Or use uv run which handles this
uv run pytest
```

**Async test issues:**
```bash
# Ensure pytest-asyncio is installed
uv add pytest-asyncio --dev
```

**Mock assertion failures:**
```python
# Check the mock was actually used
mock_drone.action.arm.assert_called_once()

# If method was called multiple times
mock_drone.action.arm.assert_called()
assert mock_drone.action.arm.call_count == 2
```

---

**Happy Testing! 🧪✈️**

