---
stepsCompleted: [1, 2]
inputDocuments:
  - project-docs/planning-artifacts/prds/prd-mqtt-mcp-server-2026-06-06/prd.md
  - project-docs/planning-artifacts/architecture.md
---

# mqtt-mcp-server — Epic Breakdown

## Overview

This document provides the complete epic and story breakdown for mqtt-mcp-server, decomposing the requirements from the PRD and Architecture documents into implementable stories.

## Requirements Inventory

### Functional Requirements

FR1: An AI agent can set an alarm on a smart clock using the `set_alarm` MCP tool with deviceId (required), alarmTime (required, RFC3339), and label (optional). DeviceId validated against `^[a-zA-Z0-9_-]{1,64}$`. AlarmTime validated as RFC3339 and not >1 min in the past. On success publishes to `{prefix}/{deviceId}/set_alarm` with JSON payload and returns `{"result": "scheduled"}`.

FR2: The server publishes alarm commands to the correct MQTT topic using format `{prefix}/{deviceId}/set_alarm` with payload `{"deviceId": "...", "type": "set_alarm", "alarmTime": "...", "label": "..."}` at configurable QoS (default 1).

FR3: An AI agent can display a message on a smart clock using the `display_message` MCP tool with deviceId (required), message (required, non-empty after trim), and durationSeconds (required, 1–3600). On success publishes to `{prefix}/{deviceId}/display_message` and returns `{"result": "sent"}`.

FR4: The server publishes message commands to topic `{prefix}/{deviceId}/display_message` with payload `{"deviceId": "...", "type": "display_message", "message": "...", "durationSeconds": N}`.

FR5: An AI agent can set brightness on a smart clock using the `set_brightness` MCP tool with deviceId (required) and level (required, 0–100). On success publishes to `{prefix}/{deviceId}/set_brightness` and returns `{"result": "updated"}`.

FR6: The server publishes brightness commands to topic `{prefix}/{deviceId}/set_brightness` with payload `{"deviceId": "...", "type": "set_brightness", "level": N}`.

FR7: An AI agent can check if the MCP server is running using the `ping` tool, which returns a simple success response immediately.

FR8: An AI agent can retrieve server metadata including MQTT broker connection status and configured topic prefix using the `server_info` tool.

FR9: The server validates configuration and MQTT broker connectivity at startup before accepting MCP tool calls. Config validation: MQTT broker URL must be present and valid. Auth credentials must be parseable. MQTT connectivity: try to connect and disconnect on startup. Exit with non-zero code on failure.

FR10: Clients must authenticate using a Bearer token. Token validation uses constant-time comparison. Tokens are scoped to devices (`*`, prefix, exact match). Multiple credentials supported. Invalid tokens return `{"error": "unauthorized"}`.

### NonFunctional Requirements

NFR1: The project must follow sonos-mcp-server's hexagonal architecture: domain → adapters → services → tools with strict layer isolation.

NFR2: The project must use Python with the same tech stack as sonos-mcp-server: `mcp[cli]`, `pydantic`, `python-dotenv`, `paho-mqtt`, `ruff`, `mypy` strict, `pytest`, `pytest-cov` (≥70%), `pip-audit`, `uv`.

NFR3: The project must use the same Makefile targets as sonos-mcp-server: `install`, `lint`, `format`, `type-check`, `test`, `coverage`, `audit`, `build-check`, `ci`.

NFR4: The project must have AGENTS.md documenting operating rules for AI agents, following sonos-mcp-server's format.

NFR5: Config must use Pydantic models with `SecretStr` for auth tokens, loaded from `.env` and `MQTT_MCP_*` environment variables.

NFR6: Domain models must be frozen dataclasses with zero infrastructure dependencies.

NFR7: All tool names must be registered in `KNOWN_TOOL_NAMES` frozenset in config/models.py — unknown names in `tools_disabled` must be rejected at startup.

NFR8: Error responses must include category, field, and suggestion for actionable AI agent recovery.

### Additional Requirements

- Server entry point: `src/mqtt_mcp/__main__.py` calling preflight → `create_server()` → run.
- Application composition in `src/mqtt_mcp/server.py::create_server()` as the single assembly point.
- MQTT adapter: paho-mqtt wrapper with connect, publish with QoS, disconnect. Implement both `ClockCommandSender` and `ReadinessChecker` interfaces.
- Tool registration in `tools/__init__.py::register_all(app, config, clock_service)`.
- Preflight validation in `config/validation.py::run_preflight()` — broker connectivity check.
- Known tool names: `ping`, `server_info`, `set_alarm`, `display_message`, `set_brightness`.
- CLI client for local debugging (optional, not required for MVP).

### FR Coverage Map

FR1, FR2: Epic 1 — Set alarm tool with validation and MQTT publishing.
FR3, FR4: Epic 1 — Display message tool with validation and MQTT publishing.
FR5, FR6: Epic 1 — Set brightness tool with validation and MQTT publishing.
FR7, FR8: Epic 1 — Setup and health tools (ping, server_info).
FR9: Epic 1 — Preflight validation and broker connectivity check.
FR10: Epic 1 — Bearer token auth with device-scoped credentials.

All FRs are covered in Epic 1. The project is small enough that a single epic delivers the MVP.

## Epic List

### Epic 1: MQTT MCP Server MVP

AI agents can control smart clocks through MCP tools — setting alarms, displaying messages, and adjusting brightness — with domain validation, MQTT publishing, Bearer auth, and preflight startup checks.

**FRs covered:** FR1 through FR10

**NFrs covered:** NFR1 through NFR8

## Epic 1: MQTT MCP Server MVP

AI agents can control smart clocks through MCP tools — setting alarms, displaying messages, and adjusting brightness — with domain validation, MQTT publishing, Bearer auth, and preflight startup checks.

### Story 1.1: Initialize Project Foundation, Config, And Domain Models

As a developer,
I want the project foundation established with sonos-mcp-server's structure, tooling, and domain models,
So that subsequent stories build on a consistent hexagonal architecture.

**Acceptance Criteria:**

**Given** the repository is ready for implementation
**When** the project foundation is initialized
**Then** the project has `pyproject.toml` with project metadata, dependencies (`mcp[cli]`, `paho-mqtt`, `pydantic`, `python-dotenv`), and tool config (ruff, mypy strict, pytest, pytest-cov ≥70%)
**And** `Makefile` with targets: `install`, `lint`, `format`, `type-check`, `test`, `coverage`, `audit`, `build-check`, `ci`
**And** the source structure matches: `src/mqtt_mcp/__main__.py`, `server.py`, `config/`, `domain/`, `adapters/`, `services/`, `tools/`, `schemas/`
**And** `uv.lock` is generated and committed.

**Given** the domain module exists
**When** domain models are implemented
**Then** `domain/models.py` has frozen dataclasses for `SetAlarmCommand`, `DisplayMessageCommand`, `SetBrightnessCommand`
**And** `domain/safety.py` has `check_brightness_level(level)`, `validate_alarm_time(alarm_time)`, `check_duration(duration_seconds)`
**And** `domain/exceptions.py` has `DomainError` with subtypes for brightness, alarm time, and message validation failures
**And** domain models import nothing from adapters, services, or tools

**Given** the config module exists
**When** config models are implemented
**Then** `config/models.py` defines `MqttConfig` pydantic model with broker URL, auth credentials (`SecretStr`), topic prefix, QoS, and `KNOWN_TOOL_NAMES` frozenset
**And** `config/defaults.py` defines `DEFAULTS` dict
**And** `config/loader.py` implements `load_config()` using DEFAULTS → `.env` → env vars (`MQTT_MCP_*`)
**And** `config/validation.py` implements `run_preflight()` that validates broker URL is reachable and credentials are parseable

**Given** the project config is complete
**When** quality gates run
**Then** `make lint` passes (ruff)
**And** `make build-check` passes (uv build --no-sources or equivalent)

### Story 1.2: Implement MQTT Adapter And Clock Service

As a developer,
I want the MQTT adapter and clock service implemented,
So that commands can be validated and published to the MQTT broker.

**Acceptance Criteria:**

**Given** the MQTT adapter module exists
**When** MqttAdapter is implemented
**Then** it wraps paho-mqtt with `connect(broker_url, username, password)`, `publish(topic, payload, qos)`, `disconnect()` methods
**And** it implements `ReadinessChecker` interface — `is_ready()` returns True/False based on connection state
**And** connection retry: up to 3 attempts with exponential backoff
**And** it raises typed exceptions on publish failure (broker unreachable, connection lost)
**And** `Close()` provides clean shutdown

**Given** the clock service module exists
**When** ClockService is implemented
**Then** it accepts `MqttAdapter` via constructor injection
**And** implements `dispatch_command(device_id, command_type, payload)` that:
  - Validates device_id against `^[a-zA-Z0-9_-]{1,64}$`
  - Builds topic as `{prefix}/{deviceId}/{commandType}`
  - Serializes payload as JSON
  - Publishes via MqttAdapter
  - Returns success/error result

**Given** the ClockService aggregates domain safety
**When** dispatch is called
**Then** it calls the appropriate domain safety function before publishing
**And** returns a typed error if validation fails, without reaching the MQTT adapter

**Given** the adapter and service are implemented
**When** tests run
**Then** MqttAdapter tests verify connect, publish, disconnect, and error states (with mocked paho-mqtt)
**And** ClockService tests verify command dispatch, topic construction, payload serialization, validation errors, and publish errors

### Story 1.3: Implement MCP Tools — Setup, Auth, And Commands

As an AI agent,
I want to call ping, server_info, set_alarm, display_message, and set_brightness as MCP tools,
So that I can check server health and control smart clocks.

**Acceptance Criteria:**

**Given** the tools module exists
**When** `tools/__init__.py::register_all()` is called
**Then** it instantiates MqttAdapter, ClockService, and registers all tools via `register_setup_support(app, config)` and `register_commands(app, config, clock_service)`
**And** each tool checks `assert_tool_permitted(tool_name, config)` before executing
**And** all tool names are in `KNOWN_TOOL_NAMES` frozenset

**Given** an agent calls `ping`
**When** the tool executes
**Then** it returns `{"status": "ok"}` immediately, with no side effects

**Given** an agent calls `server_info`
**When** the tool executes
**Then** it returns server version, MQTT broker connection status, and configured topic prefix

**Given** an agent calls `set_alarm` with valid parameters
**When** the tool executes
**Then** it validates parameters through domain safety, calls ClockService to publish, and returns `{"result": "scheduled"}`

**Given** an agent calls `set_alarm` with invalid parameters (past alarm time, bad deviceId)
**When** the tool executes
**Then** it returns a structured ErrorResponse with category "validation", the offending field, and a suggestion

**Given** an agent calls `display_message` with valid parameters
**When** the tool executes
**Then** it validates, publishes, and returns `{"result": "sent"}`

**Given** an agent calls `set_brightness` with level out of range (e.g., 150)
**When** the tool executes
**Then** it returns `ErrorResponse(category="validation", field="level", suggestion="Brightness must be 0-100")`

**Given** an invalid or missing Bearer token
**When** any command tool is called
**Then** the auth middleware rejects the call and returns an authorization error

**Given** auth middleware is configured with device-scoped credentials
**When** a command targets a device outside the token's scope
**Then** the middleware returns a forbidden error

### Story 1.4: Implement Auth, Preflight, And Server Bootstrap

As a developer,
I want auth verification, preflight startup checks, and the server entry point implemented,
So that the server boots safely and authenticates agents correctly.

**Acceptance Criteria:**

**Given** the auth module exists
**When** a tool call includes a Bearer token
**Then** auth verifier compares the token using constant-time comparison (`hmac.compare_digest`)
**And** checks the credential's device scope against the target deviceId
**And** returns unauthorized or forbidden errors for invalid/out-of-scope tokens

**Given** credentials are configured as `id|token|scope1,scope2;id2|token2|*`
**When** the server starts
**Then** all credentials are parsed and available for token verification
**And** the legacy `MQTT_MCP_AUTH_TOKEN` fallback creates a single wildcard-scope credential

**Given** the server entry point exists
**When** `__main__.py::main()` runs
**Then** it calls `run_preflight()` which:
  - Loads and validates `MqttConfig`
  - Tests MQTT broker connectivity (connect + disconnect)
  - Exits with non-zero code and descriptive error message on failure
**And** on success, calls `create_server()` then runs the server with stdio transport

**Given** preflight validation fails (e.g., broker unreachable)
**When** the server starts
**Then** the server exits immediately with an error log and does not register MCP tools

**Given** the server bootstrap is complete
**When** tests run
**Then** auth tests verify token parsing, constant-time comparison, scope matching (`*`, prefix, exact), and invalid token rejection
**And** preflight tests verify broker connectivity checking with a mock broker (success and failure paths)

### Story 1.5: AGENTS.md And Quality Gate Hardening

As a developer,
I want AGENTS.md and hardened quality gates in place,
So that AI agents can safely develop in this repo and CI gates enforce quality.

**Acceptance Criteria:**

**Given** the project is ready for documentation
**When** AGENTS.md is written
**Then** it documents: project intent, source of truth table, non-negotiable rules (safety, tool registration, testing, config), architecture rules (layer isolation, adding a new tool), BMAD integration, and CI/CD quality gates
**And** it follows the same format as sonos-mcp-server's AGENTS.md

**Given** the quality gates exist
**When** `make ci` runs
**Then** it runs lint, type-check, coverage (≥70%), audit, and build-check in sequence
**And** all targets pass

**Given** the audit target exists
**When** `make audit` runs
**Then** it runs `pip-audit` with known-build-tool CVEs documented and ignored in the Makefile (same pattern as sonos-mcp-server's pip CVE ignore)

**Given** the project is complete
**When** all quality gates run
**Then** `make lint`, `make type-check`, `make test`, `make coverage`, `make audit`, `make build-check`, and `make ci` all pass
**And** test coverage is ≥70%
