# MQTT MCP Server

A [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) server that bridges
LLM-driven workflows with IoT smart clocks via MQTT. AI agents can set alarms, display
messages, and control brightness on ESP32-based clocks through this server.

## Architecture

```
┌─────────────┐     stdio      ┌──────────────────────┐      MQTT       ┌──────────────┐
│  AI Agent   │ ◄────────────► │  mqtt-mcp-server     │ ◄────────────►  │  Smart Clock │
│  (Claude,   │                │  (FastMCP + paho)    │    topic:       │  (ESP32)     │
│   Codex,    │                │                       │  clocks/cmd/*   │              │
│   etc.)     │                └──────────────────────┘                 └──────────────┘
└─────────────┘
```

**Hexagonal architecture:**

| Layer | Location | Responsibility |
|---|---|---|
| Domain | `src/mqtt_mcp/domain/` | Validation rules, typed exceptions (zero infrastructure deps) |
| Config | `src/mqtt_mcp/config/` | Pydantic-validated settings from env/.env |
| Auth | `src/mqtt_mcp/auth.py` | Bearer token verification + device-scope authorization |
| Adapters | `src/mqtt_mcp/adapters/` | paho-mqtt wrapper (connect/publish/disconnect) |
| Services | `src/mqtt_mcp/services/` | Command dispatch, MQTT topic construction |
| Tools | `src/mqtt_mcp/tools/` | MCP tool registration (set_alarm, display_message, set_brightness) |

## Quick Start

### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) (Python package manager)
- An MQTT broker (e.g., Mosquitto) — see `docker-compose.yml` below

### Setup

```bash
git clone https://github.com/PaulKnauer/mqtt-mcp-server.git
cd mqtt-mcp-server

# Create config from template
cp .env.example .env
# Edit .env with your broker URL and credentials

# Run
uv run python -m mqtt_mcp
```

### Docker

```bash
docker build -t mqtt-mcp-server .
docker run --rm -e MQTT_MCP_BROKER_URL=mqtt://host:1883 mqtt-mcp-server
```

### Docker Compose (local MQTT broker)

```yaml
version: "3.8"
services:
  mosquitto:
    image: eclipse-mosquitto:2
    ports: ["1883:1883"]
  mqtt-mcp:
    build: .
    depends_on: [mosquitto]
    environment:
      MQTT_MCP_BROKER_URL: mqtt://mosquitto:1883
```

## Configuration

| Variable | Default | Description |
|---|---|---|
| `MQTT_MCP_BROKER_URL` | `mqtt://localhost:1883` | MQTT broker URL (`mqtt://` or `mqtts://`) |
| `MQTT_MCP_BROKER_USERNAME` | — | MQTT broker username |
| `MQTT_MCP_BROKER_PASSWORD` | — | MQTT broker password |
| `MQTT_MCP_TOPIC_PREFIX` | `clocks/commands` | MQTT topic prefix |
| `MQTT_MCP_QOS` | `1` | MQTT QoS level (0-2) |
| `MQTT_MCP_AUTH_MODE` | `none` | Auth mode (`none` or `static`) |
| `MQTT_MCP_AUTH_TOKEN` | — | Legacy bearer token (wildcard scope `*`) |
| `MQTT_MCP_AUTH_CREDENTIALS` | — | Multi-credential format: `id\|token\|scope1,scope2;id2\|token2\|*` |
| `MQTT_MCP_LOG_LEVEL` | `INFO` | Log level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |

## Tools

### `set_alarm`

Set an alarm on a smart clock device.

**Parameters:**
- `device_id` (str, required): Target device (e.g., "clock-1")
- `alarm_time` (str, required): RFC3339 UTC time (e.g., "2030-01-01T07:00:00Z")
- `label` (str, optional): Alarm label (e.g., "wake up")
- `token` (str, optional): Bearer token (required when auth is enabled)

### `display_message`

Display a message on a smart clock device.

**Parameters:**
- `device_id` (str, required): Target device
- `message` (str, required): Message text
- `duration_seconds` (int, required): Display duration (1-3600)
- `token` (str, optional): Bearer token

### `set_brightness`

Set the screen brightness.

**Parameters:**
- `device_id` (str, required): Target device
- `level` (int, required): Brightness 0-100
- `token` (str, optional): Bearer token

### `ping`

Liveness check. Returns `{"status": "ok"}`.

### `server_info`

Returns server metadata including MQTT connection state.

## MQTT Contract

### Command Topics

```
{prefix}/{deviceId}/{commandType}
```

Default: `clocks/commands/{deviceId}/{commandType}`

### Command Payloads

```json
// set_alarm
{"deviceId": "clock-1", "type": "set_alarm", "alarmTime": "2030-01-01T07:00:00Z", "label": "wake up"}

// display_message
{"deviceId": "clock-1", "type": "display_message", "message": "Meeting in 5", "durationSeconds": 30}

// set_brightness
{"deviceId": "clock-1", "type": "set_brightness", "level": 75}
```

### Device Event Topics (read-only)

| Topic | Payload | Retained |
|---|---|---|
| `clocks/events/{id}/heartbeat` | `{"uptimeSeconds": N, "wifiRssi": N, ...}` | No |
| `clocks/events/{id}/alarm_triggered` | `{"time": N, "label": "..."}` | No |
| `clocks/events/{id}/alarm_acknowledged` | `{"action": "dismiss", ...}` | No |
| `clocks/events/{id}/command_result` | `{"type": "set_alarm", "result": "applied"}` | No |
| `clocks/state/{id}/display` | `{"mode": "clock", "brightness": 50}` | Yes |
| `clocks/state/{id}/alarm` | `{"armed": true}` | Yes |
| `clocks/state/{id}/presence` | `"online"` / `"offline"` (LWT) | Yes |

## Development

```bash
# Install dev dependencies
uv sync --group dev

# Run all quality gates
make ci

# Individual gates
make lint          # ruff check + format
make type-check    # mypy strict
make test          # pytest
make coverage      # pytest with coverage (≥70%)
make audit         # pip-audit (CVE scan)
make build-check   # uv build
```

## Adding a New Tool

1. Add the domain model to `src/mqtt_mcp/domain/models.py`
2. Add validation to `src/mqtt_mcp/domain/safety.py`
3. Add a method to `src/mqtt_mcp/services/clock_service.py`
4. Add the handler to `src/mqtt_mcp/tools/commands.py`
5. Register in `src/mqtt_mcp/tools/__init__.py::register_all()`
6. Add to `KNOWN_TOOL_NAMES` in `src/mqtt_mcp/config/models.py`
7. Add tests in `tests/unit/tools/`

## Authentication

Two auth modes:

- **none**: Unrestricted access (local/home use)
- **static**: Bearer token with device-scoped credentials

Device scopes support exact match (`clock-1`), prefix match (`clock-*`), and wildcard (`*`).

Token comparison uses constant-time `hmac.compare_digest` to prevent timing attacks.

## Project Status

**Version**: 0.1.0 — Active development. Not yet production release.

## License

MIT
