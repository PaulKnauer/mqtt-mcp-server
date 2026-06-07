---
stepsCompleted: [1, 2, 3, 4]
inputDocuments:
  - project-docs/planning-artifacts/prds/prd-mqtt-mcp-server-2026-06-07/prd.md
  - project-docs/planning-artifacts/architecture.md
  - project-docs/project-context.md
---

# mqtt-mcp-server - Epic Breakdown

## Overview

This document provides the complete epic and story breakdown for mqtt-mcp-server, decomposing the requirements from the PRD, UX Design if it exists, and Architecture requirements into implementable stories.

## Requirements Inventory

### Functional Requirements

FR1: An AI agent can call `set_alarm` for a valid Device ID and future RFC3339 alarm time; the server publishes to `{topicPrefix}/{deviceId}/set_alarm` with `deviceId`, `type: "set_alarm"`, `alarmTime`, and `label`, using an empty string label when omitted and rejecting missing, malformed, timezone-less, or past alarm times with a specific validation error.

FR2: An AI agent can call `display_message` for a valid Device ID, non-empty message, and duration from 1 to 3600 seconds; the server publishes to `{topicPrefix}/{deviceId}/display_message` with `deviceId`, `type: "display_message"`, `message`, and `durationSeconds`, rejecting empty messages and out-of-range durations before publishing.

FR3: An AI agent can call `set_brightness` for a valid Device ID and brightness level from 0 to 100; the server publishes to `{topicPrefix}/{deviceId}/set_brightness` with `deviceId`, `type: "set_brightness"`, and `level`, rejecting out-of-range values before publishing.

FR4: The v1 command surface must match all command types currently supported by `clock-server`, with `clock-server` as the source of truth for topic format, command names, MQTT payload field names, tool registration, and known tool validation.

FR5: All command inputs must pass through the domain safety functions before dispatch; Device IDs are validated before topic construction, invalid input returns a specific field/category/suggestion error shape, and invalid values are never silently clamped, coerced, or ignored.

FR6: When static auth is enabled, MCP command tools require a valid token and device scope before dispatch; auth mode `none` skips checks, auth mode `static` uses constant-time bearer-token verification, device scopes support wildcard, prefix wildcard, and exact matching, and unauthorized calls do not publish MQTT commands.

FR7: A homelab user can configure broker URL, credentials, topic prefix, QoS, retained flag, and auth mode without editing source code; broker URLs, credentials, auth tokens, topic prefixes, and device IDs are not hardcoded, secrets use secret-aware config types, and validation errors name the specific field.

FR8: The server validates configuration and tool permissions before accepting traffic; unknown tool names are rejected during config validation, MQTT readiness failures surface before command handling where preflight applies, and `ping` plus `server_info` remain available for diagnostics.

FR9: An AI agent can call `get_device_state` for a valid Device ID to retrieve latest known `presence`, `display`, and `alarm` state from `clocks/state/{deviceId}/...`; missing state is reported as unavailable or unknown, and returned data preserves original payloads plus topic availability metadata.

FR10: An AI agent can call `get_recent_events` for a valid Device ID to retrieve bounded recent events for `heartbeat`, `alarm_triggered`, `alarm_acknowledged`, and `command_result`, optionally filtering by event type.

FR11: An AI agent can call `get_command_results` after publishing a command to inspect compatible-device command results with statuses `received`, `applied`, `rejected`, and `failed`; results include `deviceId`, `commandType`, `status`, `at`, and `detail`, and lack of a command result is distinct from MQTT publish success.

FR12: Read-side tools must follow `clock-server/docs/lcd-reference.md` topic names and payload fields; Device IDs are validated before subscribing to or filtering read-side topics, device-originated fields are preserved, read-side behavior is tested for topic matching, retained state, event caching, and unknown-state handling, and each read-side tool is registered through `tools/__init__.py::register_all()` and known tool validation.

### NonFunctional Requirements

NFR1: The server must be safety-first: invalid device IDs, unsafe alarm times, invalid brightness levels, empty messages, and invalid durations are rejected before MQTT publish.

NFR2: The server must preserve MQTT command and event contract fidelity with `clock-server`, including topic names and camelCase payload fields.

NFR3: The codebase must maintain strict hexagonal architecture boundaries: domain remains infrastructure-free, services own business dispatch and cache/query semantics, tools do auth and service calls, and adapters isolate paho-mqtt.

NFR4: Runtime configuration must be Pydantic v2 validated at startup, use `SecretStr` for secrets, and produce field-specific validation errors.

NFR5: Authentication must use constant-time token comparison and must not leak cached or command behavior for unauthorized device scopes when static auth is enabled.

NFR6: Read-side state must be process-local, bounded, and explicit about unavailable, unknown, or stale state rather than fabricating device status.

NFR7: The implementation must remain maintainable with Python `>=3.12`, fully typed new functions, ruff formatting, mypy strictness, and Google-style docstrings where established.

NFR8: Unit tests must cover success paths, validation failures, auth/permission behavior, exact MQTT topics and payloads, config/preflight behavior, read-side topic matching, cache bounds, retained state, recent events, command result semantics, and unknown-state behavior.

NFR9: Project quality gates must remain intact: `make lint`, `make type-check`, `make test`, `make coverage`, `make audit`, `make build-check`, and `make ci`; coverage must stay at or above the configured 70 percent floor.

NFR10: v1 must remain homelab-focused and avoid durable telemetry storage, dashboards, hosted service assumptions, broad fleet management, device discovery, OTA updates, speculative unsupported commands, or public SaaS concerns.

### Additional Requirements

- Continue from the existing repository foundation; do not introduce an external starter template.
- Preserve FastMCP from the official MCP Python SDK as the MCP server surface and register tools only through `src/mqtt_mcp/tools/__init__.py::register_all()`.
- Preserve paho-mqtt as the MQTT client library and keep all paho usage behind repository adapters.
- Add read-side behavior through adapter/service/tool layers, not direct tool-to-MQTT calls.
- Use bounded in-memory caches for retained state, recent events, and command results in v1; do not add SQLite, Redis, or another datastore.
- Keep `src/mqtt_mcp/server.py::create_server()` as the single application composition point for config, adapters, services, and tool registration.
- Apply existing static bearer-token auth and device-scope authorization to all device-scoped read and write tools.
- Treat MQTT publish success and device command-result acknowledgement as separate outcomes.
- Return unavailable or unknown read-side state explicitly; use `stale` only if a concrete freshness threshold is configured.
- Keep MQTT topic parsing and subscription callbacks outside domain models.
- Add or extend domain models only as frozen dataclasses where stable returned read-side structures need typed representation.
- Put new read-side tool handlers in a focused module such as `tools/state.py`, then wire through `tools/__init__.py`.
- Add read-side service/cache behavior in `services/device_state_service.py` and optionally `services/event_cache.py`, keeping cache mutation out of tool handlers.
- Add MQTT subscription ingestion in `adapters/mqtt_subscription_adapter.py` or a bounded extension to `adapters/mqtt_adapter.py`.
- Recognize read-side topics `clocks/events/{deviceId}/heartbeat`, `clocks/events/{deviceId}/alarm_triggered`, `clocks/events/{deviceId}/alarm_acknowledged`, `clocks/events/{deviceId}/command_result`, `clocks/state/{deviceId}/presence`, `clocks/state/{deviceId}/display`, and `clocks/state/{deviceId}/alarm`.
- Ignore or log malformed device-originated messages during MQTT callback ingestion without corrupting the cache or crashing callback execution.
- Add every new MCP tool name to `KNOWN_TOOL_NAMES` and update permissions, config/preflight validation, and `.env.example` when configuration changes.
- Place tests under `tests/unit/<layer>/` matching source ownership: adapters for topic parsing/callbacks, services for cache/query behavior, tools for auth/error responses, domain for models/safety, and config for preflight.
- Verify contract-sensitive changes against `~/github/clock-server/internal/domain/command.go`, related tests, and `clock-server/docs/lcd-reference.md`.

### UX Design Requirements

No UX Design document was provided or discovered for v1. No UI, dashboard, mobile app, or frontend bundle is in MVP scope.

### FR Coverage Map

FR1: Epic 2 - Set alarm command.

FR2: Epic 2 - Display message command.

FR3: Epic 2 - Set brightness command.

FR4: Epic 2 and Epic 3 - Contract synchronization for write-side and read-side MQTT behavior.

FR5: Epic 2 and Epic 3 - Safety validation for command inputs and device-scoped read filters.

FR6: Epic 1, Epic 2, and Epic 3 - Static auth foundation plus enforcement on command and read tools.

FR7: Epic 1 - MQTT and runtime configuration without source edits.

FR8: Epic 1 - Startup preflight, known tool validation, and diagnostics.

FR9: Epic 3 - Latest device state visibility.

FR10: Epic 3 - Recent device event visibility.

FR11: Epic 3 - Command result visibility.

FR12: Epic 3 - Read-side contract fidelity.

## Epic List

### Epic 1: Reliable Server Setup and Access Control

Users can configure, start, diagnose, and optionally protect the MCP server before device commands are handled.

**FRs covered:** FR6, FR7, FR8

### Epic 2: Safe Clock Command Control

Users can ask an AI agent to set alarms, display messages, and adjust brightness while preserving the `clock-server` MQTT command contract.

**FRs covered:** FR1, FR2, FR3, FR4, FR5, FR6

### Epic 3: Device State and Command Result Visibility

Users can ask an AI agent what a clock last reported, what recent events occurred, and whether commands were applied or rejected.

**FRs covered:** FR4, FR5, FR6, FR9, FR10, FR11, FR12

## Epic 1: Reliable Server Setup and Access Control

Users can configure, start, diagnose, and optionally protect the MCP server before device commands are handled.

### Story 1.1: Environment Configuration Loading and Validation

As a homelab user,
I want to configure MQTT and auth settings through environment variables,
So that I can run the MCP server without editing source code or exposing secrets.

**Acceptance Criteria:**

**Given** valid `MQTT_MCP_*` environment variables for broker connection, topic prefix, QoS, retained flag, and auth mode
**When** the server configuration is loaded
**Then** a validated `MqttConfig` is produced with the expected field values
**And** secret values are represented with secret-aware types.

**Given** an invalid configuration value
**When** configuration validation runs
**Then** validation fails with an error that identifies the specific field
**And** no generic-only "validation failed" message is returned.

**Given** source files in the repository
**When** configuration support is reviewed
**Then** broker URLs, credentials, auth tokens, topic prefixes, and device IDs are not hardcoded in source code
**And** `.env.example` documents supported non-secret and secret configuration inputs without containing real secrets.

### Story 1.2: Startup Preflight and Diagnostic Tool Availability

As a homelab user,
I want startup preflight checks and basic diagnostic tools,
So that configuration or permission problems are visible before command handling while I can still inspect server readiness.

**Acceptance Criteria:**

**Given** the server starts with valid configuration and known tool permissions
**When** preflight validation runs
**Then** startup readiness succeeds
**And** the server can proceed to command handling.

**Given** configured tool permissions include an unknown tool name
**When** preflight validation runs
**Then** validation fails before command handling
**And** the error identifies the unknown tool name or relevant config field.

**Given** MQTT readiness validation fails where preflight applies
**When** the server starts or validates readiness
**Then** the failure is surfaced before command tools accept traffic
**And** the failure message is specific enough to identify the readiness problem.

**Given** preflight has failed or setup is incomplete
**When** an AI agent calls `ping` or `server_info`
**Then** the diagnostic tool returns basic server/setup information
**And** the diagnostic path does not publish MQTT commands or require device authorization.

### Story 1.3: Static Token Authentication and Device Scope Enforcement

As a safety-conscious homelab operator,
I want optional static bearer-token authentication with device scopes,
So that only authorized AI agent calls can operate or inspect protected clocks.

**Acceptance Criteria:**

**Given** auth mode is `none`
**When** a device-scoped tool receives a request without a token
**Then** authentication is skipped
**And** the request proceeds to normal validation and service behavior.

**Given** auth mode is `static` and the request includes a valid bearer token
**When** token verification runs
**Then** the token is compared using constant-time comparison
**And** successful verification permits device-scope authorization to run.

**Given** auth mode is `static` and the request token is missing or invalid
**When** a device-scoped tool is called
**Then** the request is rejected before service dispatch
**And** no MQTT command is published or cached device state returned.

**Given** a verified token has device scopes configured as `*`, `clock-*`, or `clock-1`
**When** authorization checks a target Device ID
**Then** wildcard, prefix wildcard, and exact matching behave as configured
**And** unauthorized Device IDs are rejected before service dispatch.

**Given** authentication or device authorization fails
**When** the tool handler returns an error
**Then** the response uses the existing safe error shape
**And** tests cover both success and failure paths.

## Epic 2: Safe Clock Command Control

Users can ask an AI agent to set alarms, display messages, and adjust brightness while preserving the `clock-server` MQTT command contract.

### Story 2.1: Set Alarm Command Tool

As a homelab user,
I want an AI agent to set an alarm on a named clock,
So that I can schedule clock alarms without manually publishing MQTT payloads.

**Acceptance Criteria:**

**Given** a valid Device ID, future RFC3339 alarm time with timezone, and optional label
**When** an authorized AI agent calls `set_alarm`
**Then** the server validates the Device ID and alarm time through `domain/safety.py`
**And** publishes to `{topicPrefix}/{deviceId}/set_alarm`.

**Given** `set_alarm` is published
**When** the MQTT payload is serialized
**Then** it includes `deviceId`, `type: "set_alarm"`, `alarmTime`, and `label`
**And** `label` is an empty string when no label is supplied.

**Given** the Device ID is invalid, the alarm time is malformed, timezone-less, missing, or in the past
**When** `set_alarm` is called
**Then** the request is rejected with the existing safe error shape identifying the relevant field
**And** the MQTT adapter is not called.

**Given** static auth is enabled and the token or device scope is invalid
**When** `set_alarm` is called
**Then** the request is rejected before service dispatch
**And** no MQTT command is published.

**Given** the command tool surface is registered
**When** configuration validates known tool names
**Then** `set_alarm` is present in `tools/__init__.py::register_all()` and `KNOWN_TOOL_NAMES`
**And** unit tests cover success, validation failure, auth failure, and exact topic/payload shape.

### Story 2.2: Display Message Command Tool

As a homelab user,
I want an AI agent to display a temporary message on a named clock,
So that I can show reminders without manually crafting MQTT commands.

**Acceptance Criteria:**

**Given** a valid Device ID, non-empty message, and duration from 1 to 3600 seconds
**When** an authorized AI agent calls `display_message`
**Then** the server validates the Device ID, message, and duration through `domain/safety.py`
**And** publishes to `{topicPrefix}/{deviceId}/display_message`.

**Given** `display_message` is published
**When** the MQTT payload is serialized
**Then** it includes `deviceId`, `type: "display_message"`, `message`, and `durationSeconds`
**And** payload field names match the `clock-server` MQTT contract exactly.

**Given** the message is empty or the duration is below 1 or above 3600
**When** `display_message` is called
**Then** the request is rejected with the existing safe error shape identifying the relevant field
**And** the MQTT adapter is not called.

**Given** the Device ID contains invalid characters or exceeds the allowed length
**When** `display_message` is called
**Then** the request is rejected before topic construction
**And** no MQTT command is published.

**Given** static auth is enabled and the token or device scope is invalid
**When** `display_message` is called
**Then** the request is rejected before service dispatch
**And** no MQTT command is published.

**Given** the command tool surface is registered
**When** configuration validates known tool names
**Then** `display_message` is present in `tools/__init__.py::register_all()` and `KNOWN_TOOL_NAMES`
**And** unit tests cover success, validation failure, auth failure, no-publish failure, and exact topic/payload shape.

### Story 2.3: Set Brightness Command Tool

As a homelab user,
I want an AI agent to set a clock's brightness safely,
So that I can dim or brighten a named clock without publishing MQTT manually.

**Acceptance Criteria:**

**Given** a valid Device ID and brightness level from 0 to 100
**When** an authorized AI agent calls `set_brightness`
**Then** the server validates the Device ID and brightness through `domain/safety.py`
**And** publishes to `{topicPrefix}/{deviceId}/set_brightness`.

**Given** `set_brightness` is published
**When** the MQTT payload is serialized
**Then** it includes `deviceId`, `type: "set_brightness"`, and `level`
**And** payload field names match the `clock-server` MQTT contract exactly.

**Given** the brightness level is below 0 or above 100
**When** `set_brightness` is called
**Then** the request is rejected with the existing safe error shape identifying the brightness field
**And** the MQTT adapter is not called.

**Given** the Device ID is invalid
**When** `set_brightness` is called
**Then** the request is rejected before topic construction
**And** no MQTT command is published.

**Given** static auth is enabled and the token or device scope is invalid
**When** `set_brightness` is called
**Then** the request is rejected before service dispatch
**And** no MQTT command is published.

**Given** the command tool surface is registered
**When** configuration validates known tool names
**Then** `set_brightness` is present in `tools/__init__.py::register_all()` and `KNOWN_TOOL_NAMES`
**And** unit tests cover success, validation failure, auth failure, no-publish failure, and exact topic/payload shape.

### Story 2.4: Command Surface Contract and Registration Validation

As the maintainer,
I want the MCP command surface to stay synchronized with `clock-server`,
So that future command changes do not create a second or inconsistent MQTT contract.

**Acceptance Criteria:**

**Given** the v1 `clock-server` command set is `set_alarm`, `display_message`, and `set_brightness`
**When** the MCP command surface is reviewed
**Then** each supported command has a corresponding MCP tool, service dispatch path, and exact topic/payload test
**And** no speculative command tools unsupported by `clock-server` are registered.

**Given** command payload contract tests run
**When** each command is dispatched through `ClockService`
**Then** the MQTT topic format is exactly `{topicPrefix}/{deviceId}/{commandType}`
**And** payloads contain `deviceId`, `type`, and the command-specific camelCase fields expected by `clock-server`.

**Given** MCP tools are registered
**When** `register_all()` is called
**Then** command tools are registered through `tools/__init__.py` rather than side effects
**And** all command tool names appear in `KNOWN_TOOL_NAMES`.

**Given** configured permissions reference command tools
**When** preflight validates tool names
**Then** known command tools pass validation
**And** unknown or unsupported command names fail with field-specific context.

**Given** a future command is added to `clock-server`
**When** maintainers add MCP support
**Then** support is incomplete unless domain/service/tool behavior, registration, known tool validation, permissions, docs, and tests are updated together.

## Epic 3: Device State and Command Result Visibility

Users can ask an AI agent what a clock last reported, what recent events occurred, and whether commands were applied or rejected.

### Story 3.1: MQTT Read-Side Topic Ingestion and Cache Foundation

As a homelab user,
I want the server to observe clock state and event topics,
So that AI agents can answer device-status questions without manual MQTT subscriptions.

**Acceptance Criteria:**

**Given** the server is composed in `create_server()` with valid MQTT configuration
**When** read-side ingestion starts
**Then** MQTT subscription handling is created through an adapter boundary
**And** paho-mqtt details do not leak into tools or domain models.

**Given** a message arrives on `clocks/state/{deviceId}/presence`, `clocks/state/{deviceId}/display`, or `clocks/state/{deviceId}/alarm`
**When** the topic parser processes the topic
**Then** it identifies the Device ID, category `state`, and state type
**And** the latest retained-state cache is updated for the validated Device ID.

**Given** a message arrives on `clocks/events/{deviceId}/heartbeat`, `alarm_triggered`, `alarm_acknowledged`, or `command_result`
**When** the topic parser processes the topic
**Then** it identifies the Device ID, category `events`, and event type
**And** the bounded recent-event cache records the event without exceeding its configured or code-level maximum.

**Given** a topic is unrecognized, the Device ID is invalid, or the payload is malformed
**When** ingestion handles the message
**Then** the message is ignored or logged without crashing callback execution
**And** the cache is not corrupted.

**Given** unit tests run for read-side ingestion
**When** recognized and malformed topics are processed
**Then** tests cover topic matching, cache mutation, cache bounds, invalid Device IDs, and malformed payload behavior.

### Story 3.2: Latest Device State Tool

As a homelab user,
I want an AI agent to retrieve a clock's latest known state,
So that I can tell whether a named clock is online and what display or alarm state it last reported.

**Acceptance Criteria:**

**Given** a valid Device ID and cached `presence`, `display`, or `alarm` state exists
**When** an authorized AI agent calls `get_device_state`
**Then** the tool validates the Device ID through `domain/safety.py`
**And** returns the latest known state payloads with availability metadata.

**Given** no cached state exists for one or more state topics
**When** `get_device_state` is called
**Then** the response marks those state topics as unavailable or unknown
**And** does not fabricate presence, display, or alarm values.

**Given** cached device-originated state payloads include original fields from `clock-server`
**When** `get_device_state` returns data
**Then** the original payload fields are preserved
**And** any wrapper metadata clearly distinguishes topic availability from device payload content.

**Given** the Device ID is invalid
**When** `get_device_state` is called
**Then** the request is rejected before cache lookup or topic filtering
**And** the response uses the existing safe error shape.

**Given** static auth is enabled and the token or device scope is invalid
**When** `get_device_state` is called
**Then** the request is rejected before querying cached protected state
**And** no cached state is returned.

**Given** the tool is registered
**When** configuration validates known tool names
**Then** `get_device_state` is present in `tools/__init__.py::register_all()` and `KNOWN_TOOL_NAMES`
**And** unit tests cover success, unknown state, invalid Device ID, auth failure, and payload preservation.

### Story 3.3: Recent Device Events Tool

As a homelab user,
I want an AI agent to retrieve recent events for a named clock,
So that I can understand recent heartbeat, alarm, and command activity without subscribing to MQTT manually.

**Acceptance Criteria:**

**Given** a valid Device ID and recent cached events exist
**When** an authorized AI agent calls `get_recent_events`
**Then** the tool validates the Device ID through `domain/safety.py`
**And** returns bounded recent events for that Device ID.

**Given** the caller provides an event-type filter for `heartbeat`, `alarm_triggered`, `alarm_acknowledged`, or `command_result`
**When** `get_recent_events` is called
**Then** only matching event types are returned
**And** unsupported event-type filters are rejected or reported with a clear validation error.

**Given** recent events contain original device-originated payload fields
**When** `get_recent_events` returns data
**Then** original payloads are preserved
**And** wrapper metadata identifies topic, Device ID, event type, and observation time when available.

**Given** no recent events exist for the Device ID
**When** `get_recent_events` is called
**Then** the response returns an empty recent-event list or explicit unavailable state
**And** does not fabricate events.

**Given** the Device ID is invalid
**When** `get_recent_events` is called
**Then** the request is rejected before cache filtering
**And** the response uses the existing safe error shape.

**Given** static auth is enabled and the token or device scope is invalid
**When** `get_recent_events` is called
**Then** the request is rejected before querying cached protected events
**And** no cached events are returned.

**Given** the tool is registered
**When** configuration validates known tool names
**Then** `get_recent_events` is present in `tools/__init__.py::register_all()` and `KNOWN_TOOL_NAMES`
**And** unit tests cover success, event-type filtering, empty cache behavior, invalid filters, invalid Device IDs, auth failure, and cache-bound behavior.

### Story 3.4: Command Result Visibility Tool

As a homelab user,
I want an AI agent to inspect command results reported by a clock,
So that I can distinguish MQTT publish success from whether the device received, applied, rejected, or failed the command.

**Acceptance Criteria:**

**Given** cached `command_result` events exist for a valid Device ID
**When** an authorized AI agent calls `get_command_results`
**Then** the tool validates the Device ID through `domain/safety.py`
**And** returns recent command-result events for that Device ID.

**Given** the caller provides a command-type filter
**When** `get_command_results` is called
**Then** results are filtered to the requested command type
**And** the latest matching result is distinguishable from recent historical results.

**Given** a command-result payload contains `deviceId`, `commandType`, `status`, `at`, and `detail`
**When** the result is returned
**Then** status values `received`, `applied`, `rejected`, and `failed` are represented without renaming the original payload fields
**And** wrapper metadata does not obscure the device-originated payload.

**Given** no command result has been observed for the requested Device ID or command type
**When** `get_command_results` is called
**Then** the response reports that no result is available
**And** it does not treat absence of a result as MQTT publish failure.

**Given** the Device ID is invalid
**When** `get_command_results` is called
**Then** the request is rejected before cache filtering
**And** the response uses the existing safe error shape.

**Given** static auth is enabled and the token or device scope is invalid
**When** `get_command_results` is called
**Then** the request is rejected before querying cached protected command results
**And** no cached command results are returned.

**Given** the tool is registered
**When** configuration validates known tool names
**Then** `get_command_results` is present in `tools/__init__.py::register_all()` and `KNOWN_TOOL_NAMES`
**And** unit tests cover success, command-type filtering, latest-vs-recent results, no-result behavior, invalid Device IDs, auth failure, and status semantics.

### Story 3.5: Read-Side Contract, Registration, and Authorization Validation

As the maintainer,
I want read-side MCP tools to stay aligned with the `clock-server` event/state contract,
So that agents can inspect device state safely without contract drift or authorization gaps.

**Acceptance Criteria:**

**Given** the read-side topic contract from `clock-server/docs/lcd-reference.md`
**When** read-side behavior is reviewed
**Then** supported topics include `presence`, `display`, `alarm`, `heartbeat`, `alarm_triggered`, `alarm_acknowledged`, and `command_result`
**And** no unsupported read-side topics are exposed as v1 MCP behavior.

**Given** read-side payloads are returned by MCP tools
**When** state, event, or command-result responses are inspected
**Then** device-originated payload fields are preserved
**And** wrapper metadata is additive and clearly separated.

**Given** read-side tools are registered
**When** `register_all()` is called
**Then** `get_device_state`, `get_recent_events`, and `get_command_results` are registered through `tools/__init__.py` rather than side effects
**And** all three tool names appear in `KNOWN_TOOL_NAMES`.

**Given** configured permissions reference read-side tools
**When** preflight validates tool names
**Then** known read-side tools pass validation
**And** unknown read-side tool names fail with field-specific context.

**Given** static auth is enabled
**When** any read-side tool is called
**Then** token verification and device-scope authorization run before cache query behavior
**And** unauthorized requests return no cached protected state, events, or command results.

**Given** read-side tests run
**When** contract-sensitive behavior is exercised
**Then** tests cover topic names, payload preservation, registration, known tool validation, auth failure, and invalid Device ID handling.
