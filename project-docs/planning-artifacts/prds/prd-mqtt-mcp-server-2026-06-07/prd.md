---
title: mqtt-mcp-server
status: final
created: 2026-06-07
updated: 2026-06-07
---

# PRD: mqtt-mcp-server

## 0. Document Purpose

This PRD defines the v1 product requirements for `mqtt-mcp-server`, a homelab-grade MCP
server that lets AI agents control smart clock devices over MQTT. It is written for Paul as
the primary user and maintainer, and for downstream architecture, story, implementation, and
test work. The source of truth for the device command contract is `~/github/clock-server`;
this PRD captures the expected MCP surface and safety behavior, not a competing contract.

## 1. Vision

`mqtt-mcp-server` gives an AI agent a safe, typed way to operate smart clocks in a homelab.
Instead of a user manually publishing MQTT messages or remembering command payload shapes, the
agent can call MCP tools such as `set_alarm`, `display_message`, and `set_brightness`.

The product exists to bridge LLM-driven workflows and ESP32-based smart clock devices while
preserving the command contract already defined by `clock-server`. The server should feel like
a small, reliable adapter: easy to configure, strict about unsafe inputs, and transparent about
what MQTT command it published.

v1 succeeds when Paul, and other homelab users with compatible clocks, can ask an AI agent to
operate a named clock, inspect the latest device state, and trust that the MCP server publishes
or reads the correct MQTT topics and JSON payloads.

## 2. Target User

### 2.1 Jobs To Be Done

- As Paul, I want my AI agent to control my homelab smart clocks without hand-crafting MQTT
  payloads.
- As a homelab user, I want a small MCP server that exposes the current `clock-server` smart
  clock command set through agent-callable tools.
- As the maintainer, I want future command additions to stay aligned with `clock-server` rather
  than creating a second command contract.
- As a safety-conscious operator, I want invalid device IDs, unsafe alarm times, invalid
  brightness levels, empty messages, and excessive durations rejected before MQTT publish.
- As a homelab user, I want my AI agent to see whether a clock is online, what display/alarm
  state it last reported, and whether recent commands were applied or rejected.

### 2.2 Non-Users (v1)

- Users without MQTT infrastructure or compatible smart clock firmware.
- Public SaaS users who need multi-tenant account management, billing, hosted brokers, or fleet
  administration.
- Users who need long-term telemetry storage, analytics, alerting, or a dashboard over device
  events.

### 2.3 Key User Journeys

- **UJ-1. Paul asks an AI agent to display a message on a clock.** Paul is working in his
  homelab and wants a short reminder to appear on `clock-1`. He asks an AI agent to show a
  message for 30 seconds. The agent calls `display_message` with the target device, message, and
  duration. `mqtt-mcp-server` validates the inputs, publishes the MQTT command, and returns a
  success result. Paul sees the message on the clock or can inspect MQTT logs to confirm the
  command.
- **UJ-2. A homelab user schedules an alarm through an AI workflow.** A user asks their agent to
  set an alarm on a bedroom clock for a future RFC3339 time. The MCP server validates the device
  ID and alarm time, publishes the `set_alarm` command, and rejects past or malformed times with
  a specific error.
- **UJ-3. Paul adjusts clock brightness safely.** Paul asks the agent to dim a clock at night.
  The MCP server accepts brightness values from 0 to 100, rejects values outside that range, and
  publishes only valid `set_brightness` payloads.
- **UJ-4. Paul asks whether a clock is alive and what it last reported.** Paul asks an AI agent
  for the status of `clock-1`. The MCP server reads the latest retained state and recent event
  cache for that Device ID, returning presence, display state, alarm state, and recent command
  result information when available.

## 3. Glossary

- **AI agent** - An MCP client or LLM-driven tool caller that invokes `mqtt-mcp-server` tools.
- **Clock device** - A compatible ESP32-based smart clock that receives commands over MQTT.
- **Clock command** - A command supported by `clock-server` and represented as an MQTT topic plus
  JSON payload.
- **Command type** - The stable command name placed in both the MQTT topic and payload `type`
  field, such as `set_alarm`, `display_message`, or `set_brightness`.
- **Device ID** - The target clock identifier. Valid values match `^[a-zA-Z0-9_-]{1,64}$`.
- **MCP tool** - A callable tool exposed by `mqtt-mcp-server` to an AI agent.
- **MQTT command contract** - The topic and payload shape defined by `clock-server`: topic
  `{topicPrefix}/{deviceId}/{commandType}` and payloads containing `deviceId`, `type`, and
  command-specific camelCase fields.
- **MQTT event contract** - Device-originated event and state topics defined by
  `clock-server/docs/lcd-reference.md`, including `clocks/events/{deviceId}/...` and
  `clocks/state/{deviceId}/...`.
- **Retained state** - Latest MQTT state snapshot retained by the broker, such as presence,
  display state, or alarm state.
- **Topic prefix** - Configurable MQTT topic prefix. The default is `clocks/commands`.

## 4. Features

### 4.1 MCP Command Surface

**Description:** The MCP server exposes one MCP tool for each smart clock command currently
supported by `clock-server`. v1 covers `set_alarm`, `display_message`, and `set_brightness`.
Future command additions should be treated as contract-sync work: verify `clock-server`, add the
domain/service/tool behavior, register the tool, update known tool validation, and add tests.

**Functional Requirements:**

#### FR-1: Set Alarm

An AI agent can call `set_alarm` for a valid Device ID and future RFC3339 alarm time. Realizes
UJ-2.

**Consequences:**
- The server publishes to `{topicPrefix}/{deviceId}/set_alarm`.
- The payload includes `deviceId`, `type: "set_alarm"`, `alarmTime`, and `label`.
- The payload includes `label` as an empty string when no label is supplied.
- The server rejects missing, malformed, timezone-less, or unsafe past alarm times with a
  specific validation error.

#### FR-2: Display Message

An AI agent can call `display_message` for a valid Device ID, non-empty message, and display
duration from 1 to 3600 seconds. Realizes UJ-1.

**Consequences:**
- The server publishes to `{topicPrefix}/{deviceId}/display_message`.
- The payload includes `deviceId`, `type: "display_message"`, `message`, and
  `durationSeconds`.
- The server rejects empty messages and out-of-range durations before publishing.

#### FR-3: Set Brightness

An AI agent can call `set_brightness` for a valid Device ID and brightness level from 0 to 100.
Realizes UJ-3.

**Consequences:**
- The server publishes to `{topicPrefix}/{deviceId}/set_brightness`.
- The payload includes `deviceId`, `type: "set_brightness"`, and `level`.
- The server rejects brightness values below 0 or above 100 before publishing.

#### FR-4: Contract Synchronization

The v1 command surface must match all command types currently supported by `clock-server`.

**Consequences:**
- `clock-server` remains the source of truth for topic format, command type names, and MQTT
  payload field names.
- HTTP request field names from `clock-server` must not be confused with MQTT payload field
  names. MQTT payloads use camelCase fields such as `alarmTime` and `durationSeconds`.
- New command support is incomplete unless the MCP tool is registered and included in known tool
  validation.

### 4.2 Safety and Authorization

**Description:** The server rejects unsafe requests before constructing MQTT topics or
publishing commands. Auth is optional for personal homelab use but must be available for users
who want static bearer-token protection.

**Functional Requirements:**

#### FR-5: Safety Validation

All command inputs must pass through the domain safety functions before dispatch.

**Consequences:**
- Device IDs are validated before topic construction.
- Invalid input is rejected with a specific field/category/suggestion error shape.
- The server does not silently clamp, coerce, or ignore invalid values.

#### FR-6: Tool Authorization

When static auth is enabled, MCP command tools require a valid token and device scope before
dispatch.

**Consequences:**
- Auth mode `none` skips auth checks for homelab convenience.
- Auth mode `static` verifies bearer tokens using constant-time comparison.
- Device scopes support wildcard, prefix wildcard, and exact matching.
- Unauthorized calls do not publish MQTT commands.

### 4.3 Configuration and Preflight

**Description:** The server starts only with valid configuration and makes setup issues explicit.
Configuration is environment-driven and Pydantic-validated.

**Functional Requirements:**

#### FR-7: MQTT Configuration

A homelab user can configure broker URL, credentials, topic prefix, QoS, retained flag, and auth
mode without editing source code.

**Consequences:**
- Broker URLs, credentials, auth tokens, topic prefixes, and device IDs are never hardcoded in
  source code.
- Secret values use secret-aware configuration types.
- Config validation errors name the specific field that needs correction.

#### FR-8: Startup Preflight

The server validates configuration and tool permissions before accepting traffic.

**Consequences:**
- Unknown tool names are rejected during configuration validation.
- MQTT readiness failures are surfaced before command handling where preflight applies.
- Setup helper tools such as `ping` and `server_info` remain available for basic diagnostics.

### 4.4 Device State and Event Visibility

**Description:** The MCP server provides read-side tools for the device-originated MQTT topics
defined by `clock-server/docs/lcd-reference.md`. The v1 goal is homelab-useful visibility into
latest state and recent events, not a durable telemetry platform. The expected v1 runtime model
is MQTT subscription plus an in-memory cache of latest retained state and bounded recent events,
unless later architecture work chooses a different implementation.

**Functional Requirements:**

#### FR-9: Read Latest Device State

An AI agent can call `get_device_state` to request the latest known state for a valid Device ID.
Realizes UJ-4.

**Consequences:**
- The server reads or maintains latest snapshots for `clocks/state/{deviceId}/presence`.
- The server reads or maintains latest snapshots for `clocks/state/{deviceId}/display`.
- The server reads or maintains latest snapshots for `clocks/state/{deviceId}/alarm`.
- Missing state is reported as unavailable or unknown, not fabricated.
- The returned shape preserves the original state payloads and identifies which state topics are
  available, unavailable, or stale.

#### FR-10: Read Recent Device Events

An AI agent can call `get_recent_events` to request recent events for a valid Device ID. Realizes
UJ-4.

**Consequences:**
- The server recognizes `clocks/events/{deviceId}/heartbeat`.
- The server recognizes `clocks/events/{deviceId}/alarm_triggered`.
- The server recognizes `clocks/events/{deviceId}/alarm_acknowledged`.
- The server recognizes `clocks/events/{deviceId}/command_result`.
- v1 keeps a bounded in-memory recent-event cache unless a later architecture decision chooses
  durable storage.
- The tool can filter by Device ID and may optionally filter by event type.

#### FR-11: Command Result Visibility

After publishing a command, an AI agent can call `get_command_results` to inspect whether a
compatible device reported that the command was received, applied, rejected, or failed.

**Consequences:**
- Command-result status values are `received`, `applied`, `rejected`, and `failed`.
- Command-result payloads include `deviceId`, `commandType`, `status`, `at`, and `detail`.
- Command publishing remains asynchronous; lack of a command result is reported separately from
  MQTT publish success.
- The tool can return the latest result for a Device ID and command type, plus recent historical
  results within the bounded event cache.

#### FR-12: Read-Side Contract Fidelity

Read-side tools follow `clock-server/docs/lcd-reference.md` topic names and payload fields.

**Consequences:**
- The server validates Device IDs before subscribing to or filtering read-side topics.
- The server does not rename device-originated fields in returned structured data unless the
  returned shape clearly preserves the original payload.
- Read-side support is incomplete unless covered by tests for topic matching, retained state,
  recent event caching, and unknown-state behavior.
- Every read-side MCP tool must be registered through `tools/__init__.py::register_all()` and
  included in known tool validation.

## 5. Non-Goals (Explicit)

- v1 does not provide durable telemetry storage, historical analytics, or alerting for device
  events.
- v1 does not provide a UI, dashboard, mobile app, or hosted service.
- v1 does not define a new smart clock firmware contract.
- v1 does not bypass `clock-server` as the command-contract source of truth.
- v1 does not implement broad fleet management, device discovery, or OTA firmware updates.

## 6. MVP Scope

### 6.1 In Scope

- MCP tools for `set_alarm`, `display_message`, and `set_brightness`.
- MQTT publishing using `{topicPrefix}/{deviceId}/{commandType}`.
- Payloads containing `deviceId`, `type`, and command-specific camelCase fields.
- Read-side tools `get_device_state`, `get_recent_events`, and `get_command_results` for latest
  presence, display state, alarm state, heartbeat, alarm events, and command-result visibility.
- Safety validation for Device ID, alarm time, message text, duration, and brightness.
- Optional static bearer-token auth with device-scope authorization.
- Pydantic-validated startup configuration and preflight checks.
- Unit tests covering success, validation failure, auth/permission behavior, exact MQTT command
  topic/payload shape, and read-side topic/event handling.

### 6.2 Out of Scope for MVP

- Auto-discovery of clock devices from MQTT topics.
- Durable event storage, analytics, alerting, or dashboards.
- A compatibility matrix for multiple firmware versions.
- Public packaging beyond normal Python project packaging.
- Multi-user admin features.

## 7. Success Metrics

**Primary**
- **SM-1:** Paul can use an AI agent to set brightness, display a message, and set an alarm on a
  named clock without manually crafting MQTT payloads. Validates FR-1, FR-2, and FR-3.
- **SM-2:** Invalid command inputs are rejected before MQTT publish in unit tests and manual
  homelab use. Validates FR-5.
- **SM-3:** Paul can ask an AI agent for a named clock's latest known status and recent command
  result without manually subscribing to MQTT topics. Validates FR-9, FR-10, and FR-11.

**Secondary**
- **SM-4:** MQTT topic and payload tests match the current `clock-server` command and event
  contracts. Validates FR-4.
- **SM-5:** `make ci` passes before merge, including lint, type-check, coverage, audit, and build
  checks.

**Counter-metrics**
- **SM-C1:** Do not optimize for broad command count by adding speculative tools not supported
  by `clock-server`.
- **SM-C2:** Do not optimize for convenience by weakening validation, auth, or preflight errors.

## 8. Key Product Decisions

1. Alarm times accept RFC3339 values while rejecting malformed or unsafe past times.
2. `set_alarm` payloads include `label`; when no label is provided, the value is an empty string.
3. Read-side device state and event visibility are included in v1.

## 9. Validated Assumptions and Constraints

- v1 is judged by homelab usefulness and contract fidelity, not public-product completeness.
- The current `clock-server` command set is exactly `set_alarm`, `display_message`, and
  `set_brightness`.
- Other homelab users are expected to be comfortable configuring MQTT broker details and MCP
  server environment variables.
- The read-side topics in `clock-server/docs/lcd-reference.md` are stable enough to use as v1
  requirements for `mqtt-mcp-server`.
