# AGENTS.md
## AI Agent Operating Contract — MQTT MCP Server

This document defines **strict operating rules** for any AI agent (e.g. Claude Code, Codex, Cursor) working in this repository.
The goal is **safe, predictable, and reviewable** development of the MQTT MCP server for smart clock devices.

---

## 1. Project Intent (Read First)

This repository contains **MQTT MCP server**, a [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) server that exposes smart clock devices as tools for AI agents. It bridges LLM-driven workflows and IoT hardware by publishing MQTT commands to ESP32-based smart clocks running the `mqtt-smart-clock` firmware.

Key architectural commitments:
- **Hexagonal architecture** — domain models (frozen dataclasses in `src/mqtt_mcp/domain/`) have zero infrastructure dependencies. Adapters (`adapters/`) wrap the paho-mqtt library. Services (`services/`) contain business logic. Tools (`tools/`) register the MCP surface.
- **Safety-first** — brightness level, alarm time, message duration, and device ID validation are not optional. All input validation must go through `domain/safety.py`.
- **API contract** — the MQTT topic format and JSON payload shapes match the `clock-server` contract: `{topicPrefix}/{deviceId}/{commandType}` with payloads containing `deviceId`, `type`, and command-specific fields.
- **Config is Pydantic-validated** at startup — every config path has preflight validation before accepting traffic.

---

## 2. Source of Truth

### Single sources of truth (DO NOT DUPLICATE)

| Concern | Location |
|---|---|
| Server entry point | `src/mqtt_mcp/__main__.py` |
| Application composition | `src/mqtt_mcp/server.py` — `create_server()` is the single assembly point |
| Domain models | `src/mqtt_mcp/domain/models.py` — frozen dataclasses only, no infrastructure |
| Safety rules | `src/mqtt_mcp/domain/safety.py` — `check_brightness_level()`, `validate_alarm_time()`, `check_duration()`, `validate_device_id()` |
| Config schema | `src/mqtt_mcp/config/models.py` — `MqttConfig` pydantic model |
| Config validation | `src/mqtt_mcp/config/validation.py` — `run_preflight()`, `ensure_preflight_ready()` |
| MCP tool registration | `src/mqtt_mcp/tools/__init__.py` — `register_all()` |
| Authentication | `src/mqtt_mcp/auth.py` — credential parsing, token verification, device authorization |
| MQTT adapter | `src/mqtt_mcp/adapters/mqtt_adapter.py` — paho-mqtt wrapper |
| Clock service | `src/mqtt_mcp/services/clock_service.py` — command dispatch |
| Environment template | `.env.example` |

❌ **Never hardcode MQTT broker URLs, device IDs, or credentials in code.**

---

## 3. Non-Negotiable Rules

### Safety (CRITICAL)

All input validation **MUST** go through `domain/safety.py` functions:
- `check_brightness_level()` — validates 0-100 range
- `validate_alarm_time()` — validates RFC3339 format and future time
- `check_message()` — validates non-empty message
- `check_duration()` — validates 1-3600 seconds range
- `validate_device_id()` — validates `^[a-zA-Z0-9_-]{1,64}$`

Never bypass these checks. The functions raise typed `DomainError` subtypes rather than silently clamping, so the AI agent knows why the operation was rejected.

### Tool Registration

Every MCP tool MUST be registered in `tools/__init__.py::register_all()`. The tool name MUST also appear in the `KNOWN_TOOL_NAMES` frozenset in `src/mqtt_mcp/config/models.py` — otherwise the validator rejects it.

### Testing

- **Coverage floor**: `fail_under = 70` in `pyproject.toml`. Do not lower it.
- **Mypy strict mode**: `disallow_untyped_defs = true`, `disallow_incomplete_defs = true`. New code MUST be fully typed.
- **Preflight tests**: config validation and auth preflight logic MUST have tests that cover both success and failure paths.

### Config

- Never commit `.env` files. `.env` is in `.gitignore` — keep it that way.
- Secret values (`auth_token`, `broker_password`) use `SecretStr` in the Pydantic model.
- Config validation errors must surface the specific field name — never generic "validation failed" messages.

---

## 4. Architecture Rules

### Layer Isolation

```
tools/  →  services/  →  adapter/  →  paho-mqtt (external)
                ↓
         domain/models.py  (frozen dataclasses, shared across layers)
```

- **Domain** imports NOTHING from adapters, services, tools, or transports. Zero infrastructure dependencies.
- **Services** depend on adapters and domain models.
- **Tools** depend on services and config. Tools must NOT call adapters directly.
- **Auth** is checked in the tool layer before any service call.

### Adding a New Tool

1. Add the domain model to `domain/models.py` (if returning new data)
2. Add the service method to `services/clock_service.py` (or create a new service)
3. Add the tool handler in `tools/commands.py` (or a new category file)
4. Register the tool in `tools/__init__.py::register_all()`
5. Add the tool name to `KNOWN_TOOL_NAMES` in `config/models.py`
6. Add tests in `tests/unit/tools/`

### Auth Flow

```
Tool call → _authenticate(token) → parse_credentials → verify_token (constant-time)
                                   → check_device_authorization (scope matching)
```

- Auth mode `none` skips all checks
- Auth mode `static` requires a valid Bearer token
- Token comparison uses `hmac.compare_digest` (constant-time)
- Device scopes support `*`, prefix (`clock-*`), and exact (`clock-1`) matching

---

## 5. MQTT Contract

### Topic Format

```
{prefix}/{deviceId}/{commandType}
```

Default prefix: `clocks/commands`

### Command Payloads

Standard JSON shape with `deviceId`, `type`, and command-specific fields matching the `mqtt-smart-clock` firmware expectations.

### Device Events (read-only, future)

The firmware publishes event/state topics. These are not consumed by v1 of this server but the topic format is reserved:

| Topic | Description |
|---|---|
| `clocks/events/{deviceId}/heartbeat` | Periodic device status |
| `clocks/events/{deviceId}/alarm_triggered` | Alarm started |
| `clocks/events/{deviceId}/alarm_acknowledged` | Alarm dismissed |
| `clocks/events/{deviceId}/command_result` | Command acknowledgment |
| `clocks/state/{deviceId}/presence` | Online/offline (retained) |

---

## 6. CI/CD & Quality Gates

Before any merge to `main`:

- [ ] `make lint` passes (ruff check + format)
- [ ] `make type-check` passes (mypy strict)
- [ ] `make test` passes (pytest)
- [ ] `make coverage` passes (pytest-cov, ≥70%)
- [ ] `make audit` passes (pip-audit, known CVEs documented in Makefile)
- [ ] `make build-check` passes (uv build)
- [ ] `make ci` passes (lint + type-check + coverage + audit + build-check)
