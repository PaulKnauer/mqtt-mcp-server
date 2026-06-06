---
stepsCompleted: [1, 2, 3, 4, 5, 6, 7, 8]
lastStep: 8
inputDocuments:
  - project-docs/planning-artifacts/prds/prd-mqtt-mcp-server-2026-06-06/prd.md
  - project-docs/planning-artifacts/briefs/brief-mqtt-mcp-server-2026-06-06/brief.md
workflowType: 'architecture'
project_name: 'mqtt-mcp-server'
user_name: 'Paul'
date: '2026-06-06'
status: 'complete'
completedAt: '2026-06-06'
---

# Architecture Decision Document

## Project Context Analysis

### Requirements Overview

**Functional Requirements:**

The application is a Python MCP server that exposes smart clock devices as tools for AI agents. The PRD defines 10 functional requirements across five feature areas:

- Set Alarm: validate and publish alarm commands to MQTT. Topic: `{prefix}/{deviceId}/set_alarm`. Payload: `{deviceId, type, alarmTime, label}`.
- Display Message: validate and publish message commands to MQTT. Topic: `{prefix}/{deviceId}/display_message`. Payload: `{deviceId, type, message, durationSeconds}`.
- Set Brightness: validate and publish brightness commands to MQTT. Topic: `{prefix}/{deviceId}/set_brightness`. Payload: `{deviceId, type, level}`.
- Setup and Health: `ping`, `server_info` tools, and preflight broker connectivity check at startup.
- Authentication: Bearer token with device-scoped credentials, constant-time comparison.

Architecturally, this points to a focused MCP server with a small number of well-defined tools (5 total), a simple MQTT adapter for publishing, and a domain layer that validates command parameters before they reach the network.

**Non-Functional Requirements:**

The main NFRs are architecture consistency (matching sonos-mcp-server), reliability (commands reach the broker or the agent knows why), and maintainability (AGENTS.md, quality gates, test coverage).

The hexagonal architecture pattern from sonos-mcp-server requires strict layer isolation:
- Domain imports nothing from adapters, services, or tools.
- Services depend on adapters and domain models.
- Tools depend on services and config; never call adapters directly.

Quality gates from sonos-mcp-server require: make lint (ruff), make type-check (mypy strict), make test (pytest + coverage ≥70%), make audit (pip-audit), make build-check (uv build).

**Scale & Complexity:**

- Primary domain: MCP server for IoT command dispatch.
- Complexity level: low. 5 MCP tools, 1 MQTT adapter, 1 service, 3 domain validation functions.
- Estimated components: config models/loader/validation, domain models/safety/exceptions, MQTT adapter, clock service, tool registration, setup support tools, command tools, test infrastructure.

The MQTT command contract is simple and proven (clock-server already publishes the same topics). The smart-clock firmware already subscribes to the correct topics.

### Technical Constraints & Dependencies

The agreed stack matches sonos-mcp-server:
- **Runtime:** Python 3.12+
- **Package manager:** uv
- **MCP framework:** `mcp[cli]` (FastMCP with stdio transport)
- **MQTT client:** `paho-mqtt`
- **Config:** `pydantic`, `python-dotenv`
- **Linting:** `ruff`
- **Type checking:** `mypy` strict mode
- **Testing:** `pytest`, `pytest-cov` (≥70% coverage)
- **Audit:** `pip-audit`

The MQTT command contract is confirmed from clock-server source code:
- Topic format: `{prefix}/{deviceId}/{commandType}` with default prefix `clocks/commands`
- Payload shape: JSON with `deviceId`, `type`, and command-specific fields
- Device ID pattern: `^[a-zA-Z0-9_-]{1,64}$` (MQTT topic injection prevention)
- Auth model: Bearer token with device-scoped credentials (`*`, prefix, exact match)

The smart-clock firmware (`mqtt-smart-clock`) subscribes to `clocks/commands/{deviceId}/#` and expects these exact payloads.

### Cross-Cutting Concerns Identified

- Config must be validated before MQTT adapter attempts connection.
- MQTT connectivity must be verified at startup (preflight), not lazily on first tool call.
- Domain validation prevents publishing obviously invalid commands before they reach the network.
- Tool error responses must be structured and actionable for AI agents (field-level failures).
- Auth credentials are secrets and must use `SecretStr` in Pydantic models.
- The server should log each command dispatch with device ID, command type, and result.

## Core Architectural Decisions

### Decision Priority Analysis

**Critical Decisions (Block Implementation):**

- Use `mcp[cli]` as the MCP framework (FastMCP), same as sonos-mcp-server.
- Use hexagonal architecture: domain → adapters → services → tools.
- Use `paho-mqtt` as the MQTT client library.
- Use Pydantic models for config validation (matching sonos-mcp-server SoniqConfig pattern).
- Use `make` targets for all quality gates (matching sonos-mcp-server Makefile).
- Use `pyproject.toml` for project metadata and tool config.
- Publish MQTT commands to `{prefix}/{deviceId}/{commandType}` topics with JSON payloads.
- Validate deviceId, alarmTime, message, durationSeconds, and brightness level in the domain layer before publishing.

**Important Decisions (Shape Architecture):**

- Use a single `ClockService` class for all command dispatch (simpler than sonos-mcp-server's multiple service facades).
- Use a single `MqttAdapter` class wrapping paho-mqtt (one adapter, unlike sonos-mcp-server's multiple adapters).
- Auth mode: static Bearer token with device-scoped credentials, adapted from clock-server's model.
- Preflight: connect to MQTT broker and disconnect on startup; fail fast if unreachable.
- Tool registration: one file per tool category (commands.py, setup_support.py), matching sonos-mcp-server.

**Deferred Decisions (Post-MVP):**

- MCP resources/subscriptions for device events and state — deferred because the core command pattern is the product.
- HTTP transport — deferred; stdio is the simplest path to working MCP tools.
- Docker, Helm, K3s deployment — deferred until core pattern is proven.
- MQTT subscriptions for `command_result` feedback — deferred; fire-and-forget is sufficient for v1.

### Data Architecture

The server has no local database. Commands are published to MQTT topics and the server returns immediately with confirmation (or an error describing why the command couldn't be published).

Server state is minimal:
- MQTT adapter connection status (connected/disconnected).
- Config (loaded from `.env` / environment variables at startup).
- Auth credentials (loaded at startup, not reloaded at runtime).

### Authentication & Security

Bearer token authentication adapted from clock-server's model:

- **Credential format:** `id|token|scope1,scope2;id2|token2|*`
- **Token comparison:** constant-time (`hmac.compare_digest`)
- **Scope matching:** `*` (all devices), `clock-*` (prefix), `clock-1` (exact)
- **Config:** `MQTT_MCP_AUTH_CREDENTIALS` env var; legacy `MQTT_MCP_AUTH_TOKEN` fallback for single-token wildcard scope

The auth model is adapted for MCP's tool-calling context: the token is validated on each tool call, not per-request as in HTTP.

### API & Communication Patterns

The server exposes 5 MCP tools:

| Tool | Parameters | Returns |
|---|---|---|
| `ping` | none | `{"status": "ok"}` |
| `server_info` | none | `{"version": "...", "mqtt_connected": bool, "topic_prefix": "..."}` |
| `set_alarm` | `deviceId`, `alarmTime`, `label?` | `{"result": "scheduled"}` or error |
| `display_message` | `deviceId`, `message`, `durationSeconds` | `{"result": "sent"}` or error |
| `set_brightness` | `deviceId`, `level` | `{"result": "updated"}` or error |

Commands are published over MQTT with:
- QoS: configurable (default 1)
- Retained: false (commands are not retained by the broker)
- JSON payload encoding

### Server Architecture

The application follows sonos-mcp-server's hexagonal architecture:

```
┌─────────────────────────────────────────────┐
│                  TOOL LAYER                  │
│  tools/*.py — register(app, config, service) │
│  validate inputs, call service, return       │
├─────────────────────────────────────────────┤
│                 SERVICE LAYER                │
│  services/clock_service.py                  │
│  business logic, validation, dispatch        │
│  Uses domain models, calls MqttAdapter       │
├─────────────────────────────────────────────┤
│                 ADAPTER LAYER                │
│  adapters/mqtt_adapter.py — paho-mqtt       │
│  connect, publish, disconnect               │
├─────────────────────────────────────────────┤
│                 DOMAIN LAYER                 │
│  domain/models.py — frozen dataclasses       │
│  domain/safety.py — validation functions     │
│  domain/exceptions.py — typed exceptions     │
├─────────────────────────────────────────────┤
│              CONFIG + AUTH                   │
│  config/ — Pydantic models, loader, preflight│
└─────────────────────────────────────────────┘
```

### Infrastructure & Deployment

**Local development:**
- `make install` — create venv, install deps
- `make run` — start server with stdio transport (for testing with MCP Inspector or Claude Desktop)
- `make test` — run tests with coverage

**No Docker, Helm, or K3s** in v1 — deferred.

## Implementation Patterns & Consistency Rules

### Naming Patterns

**Code naming conventions:**
- Python packages: `snake_case` (e.g., `mqtt_mcp`, `clock_service`)
- Classes: `PascalCase` (e.g., `MqttConfig`, `ClockService`, `SetAlarmCommand`)
- Functions and methods: `snake_case` (e.g., `publish_command`, `check_brightness_level`)
- Constants: `UPPER_SNAKE_CASE` (e.g., `DEFAULT_TOPIC_PREFIX`, `KNOWN_TOOL_NAMES`)
- Module files: `snake_case.py` (e.g., `mqtt_adapter.py`, `clock_service.py`)

**Config env var naming:**
- Prefix: `MQTT_MCP_` (e.g., `MQTT_MCP_BROKER_URL`, `MQTT_MCP_AUTH_CREDENTIALS`)
- Consistent with sonos-mcp-server's `SONIQ_MCP_` prefix pattern

**MQTT topic naming:**
- Commands: `{prefix}/{deviceId}/{commandType}` (e.g., `clocks/commands/clock-1/set_alarm`)
- Preserves clock-server's topic format exactly

### Structure Patterns

**Project organization:**

```
src/mqtt_mcp/
├── __main__.py           # CLI entry: preflight → create_server → run
├── server.py             # create_server() — FastMCP assembly point
├── config/
│   ├── __init__.py
│   ├── models.py         # MqttConfig pydantic model + KNOWN_TOOL_NAMES
│   ├── defaults.py       # DEFAULTS dict
│   ├── loader.py         # load_config(): .env → env vars → overrides
│   └── validation.py     # run_preflight() — broker connectivity check
├── domain/
│   ├── __init__.py
│   ├── models.py         # SetAlarmCommand, DisplayMessageCommand, SetBrightnessCommand
│   ├── safety.py         # check_brightness_level(), validate_alarm_time(), check_duration()
│   └── exceptions.py     # DomainError subtypes
├── adapters/
│   ├── __init__.py
│   └── mqtt_adapter.py   # paho-mqtt wrapper: connect, publish, disconnect
├── services/
│   ├── __init__.py
│   └── clock_service.py  # ClockService — validates + dispatches commands
├── tools/
│   ├── __init__.py       # register_all() — DI + tool registration
│   ├── setup_support.py  # ping, server_info
│   └── commands.py       # set_alarm, display_message, set_brightness
├── schemas/
│   ├── __init__.py
│   ├── responses.py      # CommandResponse
│   └── errors.py         # ErrorResponse with category/field/suggestion
tests/
├── unit/
│   ├── domain/           # test_safety.py, test_models.py
│   ├── config/           # test_models.py, test_validation.py
│   ├── services/         # test_clock_service.py
│   ├── tools/            # test_commands.py, test_setup_support.py
│   ├── schemas/          # test_responses.py
│   ├── test_server.py
│   ├── test_main.py
│   └── conftest.py
```

### Error Handling Patterns

Error responses follow the same structured format as sonos-mcp-server:

```python
class ErrorResponse(BaseModel):
    error: str
    category: str  # "validation", "auth", "dispatch", "internal"
    field: str | None = None  # which input field caused the error
    suggestion: str | None = None  # actionable guidance for the AI agent
```

**Error categories:**
- `validation` — domain validation failure (bad brightness, empty message, past alarm time)
- `auth` — missing or invalid bearer token
- `dispatch` — MQTT publish failed (broker unreachable, topic invalid)
- `internal` — unexpected internal error

### Configuration Patterns

Config loading follows sonos-mcp-server's pattern:
1. `DEFAULTS` dict in `config/defaults.py`
2. `.env` file loaded by `python-dotenv`
3. `MQTT_MCP_*` environment variables override
4. Pydantic `MqttConfig` model validates everything at load time

### Enforcement Guidelines

**All AI agents MUST:**
- Keep domain models in `domain/` with zero infrastructure imports.
- Keep MQTT adapter in `adapters/` — tools must not call paho-mqtt directly.
- Validate all command inputs in `domain/safety.py` before publishing.
- Use `check_brightness_level()` for brightness validation — never bypass it.
- Register all tool names in `KNOWN_TOOL_NAMES` frozenset in config/models.py.
- Keep tests in `tests/unit/` mirroring the src structure.
- Use `SecretStr` for auth token fields in Pydantic models.
- Never hardcode MQTT broker URLs, device IDs, or credentials in source code.
- Keep AGENTS.md updated with any new architectural rules.
