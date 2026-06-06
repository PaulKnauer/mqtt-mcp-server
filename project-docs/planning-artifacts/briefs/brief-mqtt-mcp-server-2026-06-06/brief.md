---
title: "Product Brief: mqtt-mcp-server"
status: draft
created: 2026-06-06
updated: 2026-06-06
---

# Product Brief: mqtt-mcp-server

## Executive Summary

`mqtt-mcp-server` is a Model Context Protocol (MCP) server that exposes smart clock devices as tools for AI agents. It bridges the gap between LLM-driven workflows and IoT hardware by publishing MQTT commands to ESP32-based smart clocks (the `mqtt-smart-clock` firmware).

The server follows the same hexagonal architecture, MCP framework, Python tech stack, quality gates, and deployment patterns as `sonos-mcp-server`. Its API contract mirrors `clock-server`'s three command endpoints (set alarm, display message, set brightness), adapted from HTTP endpoints into MCP tools, with MQTT as the downstream transport.

## Purpose And Stakes

This project completes a home-lab IoT pipeline:

```
LLM / MCP Client → mqtt-mcp-server → MQTT Broker → mqtt-smart-clock (ESP32)
                  (MCP tools)          (mosquitto)     (display/alarm/brightness)
```

The pipeline already has `clock-server` (a Go HTTP gateway) that does the same job over HTTP. `mqtt-mcp-server` eliminates the HTTP hop by letting AI agents talk directly to the MQTT broker via native MCP tools. The smart-clock firmware already subscribes to the same MQTT topics regardless of which server publishes them.

## Primary Users

- **Paul, the home-lab owner:** wants MCP-native control over smart clocks from any MCP client (Claude Desktop, Hermes, Cursor). No HTTP gateways, no REST calls — just MCP tools.
- **AI agents (Claude, Hermes, Codex):** call `set_alarm`, `display_message`, `set_brightness` as MCP tools and receive structured responses.

## First-Version Experience

The first version should include:

- **3 MCP tools** matching clock-server's command contract: `set_alarm`, `display_message`, `set_brightness`
- **Setup tools:** `ping`, `server_info` for health checks (matching sonos-mcp-server pattern)
- **MQTT adapter** that publishes to the same topic format the smart-clock firmware expects: `clocks/commands/{deviceId}/{commandType}`
- **Config validation** preflight that checks MQTT broker connectivity at startup
- **Domain safety checks** for brightness levels, alarm times, and message duration validation
- **AGENTS.md** operating contract for AI agent development

## API Contract (from clock-server)

### Commands

| Command | MQTT Topic | Payload Fields | Validation |
|---|---|---|---|
| `set_alarm` | `clocks/commands/{deviceId}/set_alarm` | `deviceId`, `type`, `alarmTime` (RFC3339), `label` (optional) | deviceId alphanumeric 1-64 chars, alarmTime valid RFC3339, not >1 min past |
| `display_message` | `clocks/commands/{deviceId}/display_message` | `deviceId`, `type`, `message`, `durationSeconds` | deviceId valid, message non-empty, duration 1-3600 |
| `set_brightness` | `clocks/commands/{deviceId}/set_brightness` | `deviceId`, `type`, `level` (0-100) | deviceId valid, level 0-100 |

### MQTT Payload Shape

All commands publish JSON with the following structure:

```json
{
  "deviceId": "clock-1",
  "type": "set_alarm",
  "alarmTime": "2030-01-01T07:00:00Z",
  "label": "wake up"
}
```

### Topic Format

`{topicPrefix}/{deviceId}/{commandType}`

Default prefix: `clocks/commands`

### Device Events (read-only, v1 scope)

The firmware publishes to these topics (for future MCP resource exposure):

| Topic | Description |
|---|---|
| `clocks/events/{deviceId}/heartbeat` | Uptime, WiFi RSSI, NTP status, every 30-60s |
| `clocks/events/{deviceId}/alarm_triggered` | Alarm started ringing |
| `clocks/events/{deviceId}/alarm_acknowledged` | User dismissed/snoozed |
| `clocks/events/{deviceId}/command_result` | Per-command: received/applied/rejected/failed |
| `clocks/state/{deviceId}/presence` | Online/offline presence (retained) |
| `clocks/state/{deviceId}/alarm` | Current alarm schedule (retained) |
| `clocks/state/{deviceId}/display` | Current display mode + brightness (retained) |

## Product Scope

In scope for the first version:

- Python MCP server using `mcp[cli]` framework (matching sonos-mcp-server)
- Hexagonal architecture: domain → adapters → services → tools
- Pydantic-validated config loaded from `.env` and env vars
- MQTT adapter using `paho-mqtt` for publishing commands
- 3 command MCP tools plus ping/server_info setup tools
- Preflight validation: broker connectivity at startup
- Domain safety: `check_brightness_level()`, `validate_alarm_time()`, `check_duration()`
- Makefile with lint, type-check, test, audit, ci targets
- AGENTS.md AI agent operating contract
- .env.example for configuration
- Device-scoped auth (Bearer token matching clock-server's credential model)

Out of scope for the first version:

- MCP resources/tools for reading device events or state from MQTT
- HTTP transport (stdio-only for now, matching sonos-mcp-server's dual transport later)
- Docker, Helm, K3s deployment (adds complexity before core pattern is proven)
- Multiple MQTT brokers or fan-out to multiple downstreams
- Async event subscription or long-running MQTT listeners

## Acceptance Criteria

- AI agents can call `set_alarm`, `display_message`, `set_brightness` via MCP tools and receive structured responses
- Commands are published to the correct MQTT topics with the correct JSON payloads
- Domain validation rejects invalid brightness levels, empty messages, past alarm times
- Config validation rejects missing broker URL or invalid auth credentials at startup
- `make lint`, `make type-check`, `make test`, `make audit`, `make ci` all pass
- The project has AGENTS.md documenting operating rules for AI agent development
- The project follows sonos-mcp-server's directory layout, tool registration pattern, and hex architecture

## Key Decisions

- **MCP framework over raw HTTP**: direct MCP-native tools eliminate the HTTP gateway hop
- **Python over Go**: matches sonos-mcp-server's tech stack for consistency and reuse of patterns
- **paho-mqtt** as the MQTT client: the standard Python MQTT library (clock-server uses raw TCP for MQTT)
- **Sonos hex architecture**: domain/adapter/service/tool isolation proven in sonos-mcp-server
- **sonos-mcp-server project structure**: same Makefile, pyproject.toml, test layout, and quality gates
- **clock-server API contract**: same topic format, payload structure, validation rules, and device ID pattern
- **stdio transport first**: simplest path to working MCP tools; HTTP transport deferred

## Open Questions

- Should the MQTT adapter subscribe to retained state topics so MCP tools can expose device state?
- What authentication model for the MQTT broker (username/password, TLS client certs)?
- Should the server also subscribe to `command_result` topics for synchronous feedback?
- Should the server support MQTT TLS or plain TCP?

## Next Step

Use the Architect Agent next to produce `architecture.md` and then decompose into epics and stories in `epics.md`.
