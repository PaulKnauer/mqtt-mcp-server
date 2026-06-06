---
title: "PRD: mqtt-mcp-server"
status: draft
created: 2026-06-06
updated: 2026-06-06
---

# PRD: mqtt-mcp-server

## 0. Document Purpose

This PRD defines the first product version of `mqtt-mcp-server`, a Python MCP server that exposes smart clock devices as tools for AI agents. It is written for architecture and implementation follow-up. Features are grouped by capability, functional requirements use stable `FR-N` IDs, and assumptions are tagged inline and indexed in section 8.

## 1. Vision

`mqtt-mcp-server` lets AI agents control ESP32-based smart clocks through MCP tools — setting alarms, displaying messages, and adjusting brightness — by publishing MQTT commands in the format the `mqtt-smart-clock` firmware already expects.

The server eliminates the HTTP gateway hop that `clock-server` required, giving AI agents direct MQTT-native control. It follows `sonos-mcp-server`'s proven hexagonal architecture, Python MCP stack, Makefile quality gates, and project conventions so the codebase is immediately familiar and maintainable.

## 2. Target User

### 2.1 Primary Persona

**Paul, the home-lab owner**, has smart clocks running `mqtt-smart-clock` firmware on his home network. He wants to control them from any MCP client — Claude Desktop, Hermes, Cursor — without needing an HTTP gateway. He cares about safety (can't set brightness past 100), reliability (commands reach the device), and debuggability (server tells him what happened).

### 2.2 Secondary Personas

- **AI agents (Claude, Hermes, Codex):** call MCP tools and receive structured success/failure responses.
- **Paul as developer:** needs a predictable hex-arch codebase with AGENTS.md guardrails, familiar Makefile targets, and quality gates matching sonos-mcp-server.

### 2.3 Jobs To Be Done

- Set an alarm on a specific clock device from an AI chat.
- Display a message on a clock screen (reminder, notification, smart-home event).
- Adjust clock brightness for daytime/nighttime.
- Verify the MCP server is running and the MQTT broker is reachable.
- Know whether a command succeeded or failed, and why.

### 2.4 Key User Journeys

- **UJ-1. Paul asks an AI agent to set an alarm.** Paul says "set an alarm on the kitchen clock for 7am tomorrow". The AI agent calls `set_alarm` MCP tool. The server validates the time, publishes to `clocks/commands/clock-kitchen/set_alarm`, and returns `{"result": "scheduled"}`.
- **UJ-2. An AI displays a message on a clock.** A Hermes automation detects a calendar event and calls `display_message` on the office clock. The server validates the message and duration, publishes to MQTT, and returns confirmation.
- **UJ-3. A brightness command fails validation.** An agent calls `set_brightness` with level 150. The server's domain safety layer rejects it with a clear explanation. The agent can retry with a valid level.
- **UJ-4. Paul checks server health.** Paul's workflow calls `ping` or `server_info` to verify the MCP server and MQTT broker are reachable before sending commands.

## 3. Glossary

- **Smart Clock** — An ESP32 device running `mqtt-smart-clock` firmware, connected to the home WiFi and MQTT broker, with an ILI9341 display, alarm, and touch controls.
- **MCP Tool** — A function exposed by the MCP server that AI agents can call. Each tool has a name, description, and typed parameters.
- **MQTT Topic** — The pub/sub channel for clock commands, formatted as `{prefix}/{deviceId}/{commandType}`.
- **Device ID** — A unique identifier for each smart clock (`^[a-zA-Z0-9_-]{1,64}$`), preventing MQTT topic injection.
- **Preflight Validation** — Startup checks that verify MQTT broker connectivity and config validity before accepting MCP tool calls.

## 4. Features

### 4.1 Set Alarm

**Description:** Schedule an alarm on a target smart clock device. Realizes UJ-1.

**Functional Requirements:**

#### FR-1: Set Alarm

An AI agent can set an alarm on a smart clock using the `set_alarm` MCP tool.

**Consequences:**
- The tool accepts `deviceId` (string, required), `alarmTime` (string, RFC3339 format), and optional `label` (string).
- The server validates `deviceId` against `^[a-zA-Z0-9_-]{1,64}$`.
- The server validates `alarmTime` is valid RFC3339 and not more than 1 minute in the past.
- On success, the server publishes to `{prefix}/{deviceId}/set_alarm` and returns `{"result": "scheduled"}`.
- On validation failure, the server returns a structured error explaining which field failed and why.

#### FR-2: Publish Alarm to Correct MQTT Topic

The server uses the correct MQTT topic format matching the smart-clock firmware subscription.

**Consequences:**
- Topic format: `{prefix}/{deviceId}/set_alarm` where `prefix` defaults to `clocks/commands`.
- Payload: `{"deviceId": "...", "type": "set_alarm", "alarmTime": "...", "label": "..."}`.
- QoS is configurable (default 1) matching clock-server's MQTT sender.

### 4.2 Display Message

**Description:** Display a message on a target smart clock's screen. Realizes UJ-2.

**Functional Requirements:**

#### FR-3: Display Message

An AI agent can display a message on a smart clock using the `display_message` MCP tool.

**Consequences:**
- The tool accepts `deviceId` (string, required), `message` (string, required), and `durationSeconds` (integer, required).
- The server validates `deviceId` is valid.
- The server validates `message` is non-empty after trimming whitespace.
- The server validates `durationSeconds` is 1–3600 inclusive.
- On success, the server publishes to `{prefix}/{deviceId}/display_message` and returns `{"result": "sent"}`.

#### FR-4: Publish Message to Correct MQTT Topic

**Consequences:**
- Topic format: `{prefix}/{deviceId}/display_message`.
- Payload: `{"deviceId": "...", "type": "display_message", "message": "...", "durationSeconds": N}`.

### 4.3 Set Brightness

**Description:** Adjust screen brightness on a target smart clock. Realizes UJ-3.

**Functional Requirements:**

#### FR-5: Set Brightness

An AI agent can set the brightness level on a smart clock using the `set_brightness` MCP tool.

**Consequences:**
- The tool accepts `deviceId` (string, required) and `level` (integer, required, 0–100).
- The server validates `deviceId` is valid.
- The server validates `level` is 0–100 inclusive.
- On success, the server publishes to `{prefix}/{deviceId}/set_brightness` and returns `{"result": "updated"}`.

#### FR-6: Publish Brightness to Correct MQTT Topic

**Consequences:**
- Topic format: `{prefix}/{deviceId}/set_brightness`.
- Payload: `{"deviceId": "...", "type": "set_brightness", "level": N}`.

### 4.4 Setup and Health

**Description:** Basic server health and connectivity checks. Realizes UJ-4.

**Functional Requirements:**

#### FR-7: Ping

An AI agent can check if the MCP server is running using the `ping` tool.

**Consequences:**
- Returns a simple success response immediately, with no side effects.

#### FR-8: Server Info

An AI agent can retrieve server metadata including MQTT broker status and configured devices.

**Consequences:**
- Returns server version, MQTT broker connection status, and configured topic prefix.

#### FR-9: Preflight Validation

The server validates configuration and MQTT broker connectivity at startup before accepting MCP tool calls.

**Consequences:**
- Config validation: MQTT broker URL must be present and valid. Device auth credentials must be parseable.
- MQTT connectivity: the server attempts to connect to the broker and disconnect on startup.
- If preflight fails, the server logs the specific failure and exits with a non-zero code.
- The server does not register MCP tools or accept connections until preflight passes.

### 4.5 Authentication

**Description:** Bearer token authentication matching clock-server's credential model for consistency.

**Functional Requirements:**

#### FR-10: Bearer Token Auth

Clients must authenticate using a Bearer token in the MCP session.

**Consequences:**
- Token validation uses constant-time comparison (matching clock-server's `crypto/subtle.ConstantTimeCompare` pattern).
- Tokens are scoped to devices: `*` (all devices), `clock-*` (prefix match), or `clock-1` (exact match).
- Multiple credentials can be configured, each with its own token and device scope.
- Invalid or missing tokens return `{"error": "unauthorized"}`.
- This aligns with clock-server's `API_AUTH_CREDENTIALS` model, adapted for MCP transport.

## 5. Non-Goals

- No MCP resources or subscriptions for reading device events or retained state in v1.
- No HTTP transport in v1 (stdio only, matching sonos-mcp-server but HTTP deferred).
- No Docker, Helm, K3s deployment artifacts in v1.
- No multiple MQTT broker support or fan-out to multiple downstreams.
- No async MQTT event listeners or long-running subscriptions.
- No device discovery (device IDs are configured statically).
- No firmware updates or OTA management for smart clocks.
- No clock-server API compatibility beyond the MQTT command contract.

## 6. MVP Scope

### 6.1 In Scope

- MCP server with 5 tools: `ping`, `server_info`, `set_alarm`, `display_message`, `set_brightness`.
- MQTT adapter publishing commands to the broker.
- Domain validation for all command parameters.
- Pydantic-validated config from `.env` and environment variables.
- Bearer token auth with device-scoped credentials.
- Preflight validation: broker connectivity check at startup.
- Hexagonal architecture: domain/ → adapters/ → services/ → tools/.
- AGENTS.md operating contract.
- Makefile with lint, type-check, test, audit, ci targets.
- test suite with pytest, coverage minimum 70%.
- mypy strict mode, ruff lint/format.

### 6.2 Out of Scope for MVP

- MCP resources or subscriptions for device events.
- HTTP transport.
- Docker, Helm, K3s deployment.
- Multiple MQTT brokers.
- Async event listeners.
- Device discovery.

## 7. Success Metrics

**Primary**

- **SM-1:** An AI agent can call `set_alarm`, `display_message`, and `set_brightness` against a real MQTT broker and the correct MQTT topics receive the correct JSON payloads. Validates FR-1 through FR-6.
- **SM-2:** A developer can run `make ci` and all quality gates pass (lint, type-check, test coverage ≥70%, audit, build-check). Validates project structure quality.
- **SM-3:** Domain validation rejects invalid inputs (level out of range, empty message, past alarm time) with structured error responses. Validates FR-1, FR-3, FR-5.

**Secondary**

- **SM-4:** The server exits on startup if MQTT broker is unreachable. Validates FR-9.
- **SM-5:** An agent with an invalid token receives an authorization error. Validates FR-10.

**Counter-metrics**

- **SM-C1:** Do not optimize for feature count. Adding HTTP transport, Docker, or event subscriptions before the core MCP tool pattern is proven would dilute quality.
- **SM-C2:** Do not optimize for backward compatibility with clock-server HTTP endpoints. The MCP tool contract is the product.

## 8. Assumptions Index

- FR-1: `alarmTime` sanity check of "not more than 1 minute in the past" is sufficient; the firmware handles forwarding alarms that are in the future.
- General: The MQTT broker is already running in the home lab and does not need deployment from this project.
- General: The smart-clock firmware is already deployed and subscribes to the correct topics.
- General: paho-mqtt is the correct Python MQTT library for this use case.
