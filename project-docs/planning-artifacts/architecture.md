---
stepsCompleted: [1, 2, 3, 4, 5, 6, 7, 8]
inputDocuments:
  - project-docs/planning-artifacts/prds/prd-mqtt-mcp-server-2026-06-07/prd.md
  - project-docs/project-context.md
workflowType: "architecture"
project_name: "mqtt-mcp-server"
user_name: "Paul"
date: "2026-06-07"
lastStep: 8
status: "complete"
completedAt: "2026-06-07"
---

# Architecture Decision Document

_This document builds collaboratively through step-by-step discovery. Sections are appended as we work through each architectural decision together._

## Project Context Analysis

### Requirements Overview

**Functional Requirements:**
The PRD defines 12 functional requirements. FR-1 through FR-4 cover the command surface for `set_alarm`, `display_message`, and `set_brightness`, including strict alignment with the `clock-server` MQTT topic and payload contract. FR-5 and FR-6 define safety validation and optional static bearer-token authorization. FR-7 and FR-8 define environment-driven Pydantic configuration and startup preflight. FR-9 through FR-12 add read-side visibility for retained device state, recent device events, and command results.

Architecturally, this is a small backend integration server with two clear planes: a write-side command path that validates and publishes MQTT commands, and a read-side observation path that subscribes to clock state/event topics and maintains bounded in-memory snapshots for MCP tools.

**Non-Functional Requirements:**
The major non-functional drivers are safety, contract fidelity, maintainability, and predictable local operation. Inputs must be rejected before MQTT publish when unsafe. Device IDs must be validated before topic construction or subscription filtering. The command and event contracts must remain aligned with `clock-server`. Runtime configuration must fail early with field-specific validation errors. The codebase must preserve strict typing, ruff formatting, mypy strictness, and the configured coverage floor.

**Scale & Complexity:**

- Primary domain: Python backend integration service / MCP server
- Complexity level: medium
- Estimated architectural components: MCP tool layer, auth/permissions layer, command service, MQTT adapter, read-side subscription adapter or event listener, in-memory state/event cache, config/preflight validation, domain safety/model layer, tests

### Technical Constraints & Dependencies

The implementation must preserve the existing hexagonal architecture. Domain models and safety functions remain infrastructure-free. Tools authenticate and authorize before service calls and never call paho-mqtt directly. MQTT library usage stays behind `src/mqtt_mcp/adapters/mqtt_adapter.py` or a clearly bounded adapter extension. Application composition remains centralized in `src/mqtt_mcp/server.py::create_server()`.

The command topic format is `{topicPrefix}/{deviceId}/{commandType}` and command payloads must include `deviceId`, `type`, and command-specific camelCase fields. Read-side topics and payloads must follow `clock-server/docs/lcd-reference.md`. Configuration uses Pydantic v2 and `SecretStr` for secrets. Tool names must be registered through `tools/__init__.py::register_all()` and included in `KNOWN_TOOL_NAMES`.

### Cross-Cutting Concerns Identified

Safety validation affects every command and read-side tool that accepts a Device ID or user input. Authorization affects all device-scoped tools when static auth is enabled. MQTT contract fidelity affects services, adapters, tool return shapes, and tests. Preflight validation affects startup behavior, known tool validation, MQTT readiness, and diagnostic tools. Observability of command results introduces asynchronous semantics: MQTT publish success is separate from device acknowledgement or rejection. Read-side caching must be bounded, in-memory, and explicit about unavailable or stale state rather than fabricating device status.

## Starter Template Evaluation

### Primary Technology Domain

Python backend integration service / MCP server, based on the existing repository and PRD requirements.

### Starter Options Considered

No external starter template should be introduced. The project already has the foundation that a starter would normally provide: Python package metadata in `pyproject.toml`, `uv`-managed dependencies, FastMCP from the official MCP Python SDK, strict mypy settings, ruff lint/format configuration, pytest/coverage configuration, and an established `src/` package layout.

The official MCP Python SDK documentation confirms that Python is a Tier 1 SDK and that FastMCP is the core interface for building MCP servers. The current `uv` documentation confirms `uv init` as the normal project creation path, but this repository has already passed that initialization point.

### Selected Starter: Existing Repository Foundation

**Rationale for Selection:**
The existing codebase is the correct starter. Introducing a new template would create churn and risk weakening the established architecture rules. The project already has stronger repo-specific structure than a generic starter: hexagonal layer boundaries, Pydantic configuration, MQTT adapter isolation, safety validation, auth flow, tests, and Makefile quality gates.

**Initialization Command:**

```bash
# No starter initialization command.
# Continue from the existing repository foundation.
```

**Architectural Decisions Provided by Starter:**

**Language & Runtime:**
Python `>=3.12` with modern typing syntax and strict mypy enforcement.

**Styling Solution:**
Not applicable. This is a backend MCP server with no UI.

**Build Tooling:**
`uv_build` via `pyproject.toml`, with `uv` used for dependency and project workflow.

**Testing Framework:**
`pytest` with `pytest-cov`, a configured coverage floor, and unit tests organized by architecture layer.

**Code Organization:**
Existing `src/mqtt_mcp` package organized into domain, config, adapters, services, tools, auth, logging, server composition, and entrypoint modules.

**Development Experience:**
Makefile quality gates cover linting, type checking, tests, coverage, audit, build checks, and aggregate CI. Ruff handles linting and formatting. Mypy enforces typed functions.

## Core Architectural Decisions

### Decision Priority Analysis

**Critical Decisions (Block Implementation):**

- Preserve the existing hexagonal architecture and add read-side behavior through services and adapters, not direct tool-to-MQTT calls.
- Use bounded in-memory caches for retained state, recent events, and command results in v1.
- Keep paho-mqtt as the only MQTT client library, wrapped behind repository adapters.
- Keep FastMCP from the official MCP Python SDK as the MCP server surface.
- Keep Pydantic v2 configuration and preflight validation as the startup gate.
- Apply existing static bearer-token auth and device-scope authorization to all device-scoped read and write tools.

**Important Decisions (Shape Architecture):**

- Treat command publish success and device command-result acknowledgement as separate outcomes.
- Return unavailable, unknown, or stale read-side state explicitly rather than fabricating device status.
- Keep read-side topic parsing and MQTT subscription handling outside domain models.
- Continue using Makefile quality gates as the implementation readiness standard.

**Deferred Decisions (Post-MVP):**

- Durable telemetry storage is deferred because the PRD explicitly limits v1 to bounded in-memory visibility.
- Device auto-discovery is deferred because it is out of MVP scope.
- UI/dashboard architecture is not applicable for v1.
- Multi-user administration and hosted deployment architecture are deferred because v1 targets homelab operation.

### Data Architecture

The v1 data architecture is in-memory and process-local. No database is introduced.

Retained state snapshots should be modeled as latest-known values keyed by Device ID and state topic category: presence, display, and alarm. Recent events should use bounded per-device collections with a configurable or code-level default maximum. Command results should be derived from the recent event stream and indexed enough to answer latest-result queries by Device ID and command type.

Domain models may represent returned state and event records as frozen dataclasses, but MQTT parsing, subscription callbacks, cache mutation, and topic matching remain infrastructure/service concerns.

### Authentication & Security

Auth mode remains `none` or `static` as currently defined. Device-scoped command and read tools must authenticate before dispatch when static auth is enabled.

Token verification continues to use constant-time comparison. Device authorization continues to support wildcard, prefix wildcard, and exact device scopes. Unauthorized calls must not publish commands, subscribe to new device-specific filters on behalf of the request, or return cached state for unauthorized devices.

All Device IDs must pass through `validate_device_id()` before topic construction, cache lookup, subscription filtering, or returned result filtering.

### API & Communication Patterns

The public API is MCP tools registered through FastMCP. No REST, GraphQL, or additional HTTP API is introduced for v1.

Write-side tools publish MQTT commands asynchronously and return MQTT publish outcome only. Device acknowledgement is exposed separately through `get_command_results`.

Read-side tools return structured MCP tool results from the in-memory observation cache:

- `get_device_state` returns latest known retained state by requested Device ID.
- `get_recent_events` returns bounded recent events, optionally filtered by event type.
- `get_command_results` returns latest and recent command-result events for a Device ID and optional command type.

MQTT topic and payload names remain contract-driven by `clock-server`. Tool return shapes may wrap device payloads with metadata, but must preserve original device-originated payloads rather than silently renaming fields.

### Frontend Architecture

Not applicable. v1 has no UI, dashboard, mobile app, or frontend bundle.

### Infrastructure & Deployment

The runtime remains a local Python MCP server started from the existing package entrypoint. Application composition remains centralized in `src/mqtt_mcp/server.py::create_server()`.

MQTT connection setup and read-side subscription startup should be composed at server creation or an explicit startup/preflight boundary. Startup must fail early for invalid configuration, while diagnostic tools such as `ping` and `server_info` remain available according to existing preflight behavior.

Quality gates remain:

- `make lint`
- `make type-check`
- `make test`
- `make coverage`
- `make audit`
- `make build-check`
- `make ci`

### Decision Impact Analysis

**Implementation Sequence:**

1. Extend domain models only where returned read-side structures need stable typed representation.
2. Add read-side MQTT topic parsing and bounded cache behavior behind services/adapters.
3. Compose MQTT subscription startup in the existing server assembly path.
4. Add MCP read tools through the existing tools registration flow.
5. Update `KNOWN_TOOL_NAMES`, permissions, config/preflight validation, and `.env.example` if configuration changes.
6. Add unit tests for topic matching, cache behavior, unknown/stale state, auth failures, and command-result semantics.
7. Run the existing quality gates before merge.

**Cross-Component Dependencies:**
Read-side tools depend on the cache service, auth helpers, and config. The cache service depends on MQTT event ingestion but not FastMCP. MQTT ingestion depends on the paho adapter layer. Domain safety remains the single validation path for Device IDs and command inputs. Config preflight must know every registered tool name so permission validation stays consistent with the MCP surface.

## Implementation Patterns & Consistency Rules

### Pattern Categories Defined

**Critical Conflict Points Identified:**
Eight areas need explicit consistency rules: Python naming, module placement, MCP tool registration, MQTT topic/payload formats, read-side cache shape, error response shape, auth/validation ordering, and test placement.

### Naming Patterns

**Database Naming Conventions:**
Not applicable for v1. No database tables, migrations, indexes, or persistent schemas should be introduced.

**API Naming Conventions:**
The public API is MCP tool names. Tool names use lower snake_case and must match `KNOWN_TOOL_NAMES` exactly.

Examples:

- `set_alarm`
- `display_message`
- `set_brightness`
- `get_device_state`
- `get_recent_events`
- `get_command_results`

MQTT command payload fields preserve the external contract and use camelCase where `clock-server` expects camelCase.

Examples:

- `deviceId`
- `alarmTime`
- `durationSeconds`
- `commandType`

**Code Naming Conventions:**
Python modules, functions, variables, and test files use snake_case. Classes and dataclasses use PascalCase. Constants use UPPER_SNAKE_CASE.

Read-side implementation names should use consistent vocabulary:

- `state` for retained latest device state
- `event` for device-originated event messages
- `command_result` for command acknowledgement events
- `cache` for bounded in-memory storage
- `topic` for MQTT topic parsing and construction

### Structure Patterns

**Project Organization:**
Keep the existing layer structure:

- `domain/` contains frozen dataclasses, typed domain errors, and safety validation only.
- `adapters/` contains paho-mqtt interaction and MQTT callback integration.
- `services/` contains command dispatch, read-side cache/query behavior, and business rules.
- `tools/` contains FastMCP tool handlers, auth checks, permission checks, and safe response shaping.
- `config/` contains Pydantic models, environment loading, defaults, and preflight validation.

New read-side tool handlers should go in a separate `tools/state.py` or similarly specific module, then be wired through `tools/__init__.py::register_all()`. They should not be added as side effects or registered directly from `server.py`.

**File Structure Patterns:**
Tests stay under `tests/unit/<layer>/` matching the source layer:

- Topic parsing and adapter callback tests under `tests/unit/adapters/`
- Cache/query service tests under `tests/unit/services/`
- Tool behavior tests under `tests/unit/tools/`
- Domain model/safety tests under `tests/unit/domain/`
- Config/preflight tests under `tests/unit/config/`

### Format Patterns

**API Response Formats:**
Tool handlers return plain `dict[str, object]` structures compatible with existing command tools.

Errors use the existing safe error shape:

- `error`
- `category`
- `field` for domain validation errors
- `suggestion` for domain validation errors

Read-side tools should use explicit availability metadata instead of fabricating state. Missing retained state should be represented as unavailable or unknown.

**Data Exchange Formats:**
MQTT command payloads keep `clock-server` field names exactly. Device-originated MQTT payloads returned by read-side tools must be preserved as original payload dictionaries, wrapped with metadata when needed.

Dates and times use RFC3339/ISO 8601 strings with explicit timezone. Do not introduce Unix timestamps unless the upstream device contract already provides them.

### Communication Patterns

**Event System Patterns:**
MQTT topics are the event boundary. Do not introduce a second internal event bus for v1.

Recognized read-side topics:

- `clocks/events/{deviceId}/heartbeat`
- `clocks/events/{deviceId}/alarm_triggered`
- `clocks/events/{deviceId}/alarm_acknowledged`
- `clocks/events/{deviceId}/command_result`
- `clocks/state/{deviceId}/presence`
- `clocks/state/{deviceId}/display`
- `clocks/state/{deviceId}/alarm`

Topic parsing should produce typed internal records or structured parse results before cache mutation. Invalid or unrecognized topics should be ignored or logged without raising through MQTT callback execution.

**State Management Patterns:**
The read-side cache is bounded and in-memory. Cache mutation belongs in a service or dedicated cache object, not in MCP tool handlers. Tool handlers query the service.

Cache keys use validated Device IDs and normalized event/state type strings from the MQTT topic. Per-device recent event lists must enforce bounds at insertion time.

### Process Patterns

**Error Handling Patterns:**
Tool handlers catch `MqttMCPError` and return `_safe_error(...)`-compatible dictionaries. Domain validation failures should use typed `DomainError` subclasses. MQTT callback ingestion should log malformed device messages and continue processing later messages.

Do not silently clamp, coerce, or ignore user-provided command inputs. Device-originated malformed payloads may be ignored as ingestion failures, but should not corrupt the cache.

**Loading State Patterns:**
Not applicable for UI. For device state, use availability language:

- `available` when a latest payload exists
- `unavailable` or `unknown` when no payload has been observed
- `stale` only when the architecture has a configured freshness threshold

### Enforcement Guidelines

**All AI Agents MUST:**

- Validate Device IDs through `validate_device_id()` before topic construction, cache lookup, or device-scoped filtering.
- Register every new MCP tool through `tools/__init__.py::register_all()` and add its name to `KNOWN_TOOL_NAMES`.
- Keep paho-mqtt calls behind adapter code.
- Preserve `clock-server` MQTT topic and payload field names.
- Add tests in the matching `tests/unit/<layer>/` folder for success and failure paths.

**Pattern Enforcement:**
Pattern compliance is verified through code review plus `make lint`, `make type-check`, `make test`, and `make coverage`. Contract-sensitive changes must include exact topic and payload assertions. Config or tool-surface changes must include preflight tests.

### Pattern Examples

**Good Examples:**

- A `get_device_state` tool authenticates, validates `device_id`, asserts tool permission, queries a state service, and returns cached payloads with availability metadata.
- A topic parser accepts `clocks/events/clock-1/command_result` and returns `{device_id: "clock-1", category: "events", event_type: "command_result"}` or an equivalent typed structure.
- A service test asserts that recent events are capped to the configured maximum after insertion.

**Anti-Patterns:**

- Calling `adapter.publish()` or paho-mqtt directly from a tool handler.
- Building MQTT topics before `validate_device_id()`.
- Returning renamed device payload fields without preserving the original payload.
- Adding `get_device_state` to FastMCP but forgetting `KNOWN_TOOL_NAMES`.
- Introducing SQLite, Redis, or another datastore for v1 read-side state.

## Project Structure & Boundaries

### Complete Project Directory Structure

```text
mqtt-mcp-server/
├── AGENTS.md
├── Dockerfile
├── LICENSE
├── Makefile
├── README.md
├── pyproject.toml
├── uv.lock
├── .dockerignore
├── .env.example
├── .gitignore
├── project-docs/
│   ├── project-context.md
│   └── planning-artifacts/
│       ├── architecture.md
│       └── prds/
│           └── prd-mqtt-mcp-server-2026-06-07/
│               ├── prd.md
│               ├── reconcile-clock-server.md
│               ├── reconcile-project-context.md
│               └── review-rubric.md
├── src/
│   └── mqtt_mcp/
│       ├── __init__.py
│       ├── __main__.py
│       ├── auth.py
│       ├── logging.py
│       ├── server.py
│       ├── adapters/
│       │   ├── __init__.py
│       │   ├── mqtt_adapter.py
│       │   └── mqtt_subscription_adapter.py        # v1 read-side addition if separated
│       ├── config/
│       │   ├── __init__.py
│       │   ├── defaults.py
│       │   ├── loader.py
│       │   ├── models.py
│       │   └── validation.py
│       ├── domain/
│       │   ├── __init__.py
│       │   ├── exceptions.py
│       │   ├── models.py
│       │   └── safety.py
│       ├── services/
│       │   ├── __init__.py
│       │   ├── clock_service.py
│       │   ├── device_state_service.py             # v1 read-side addition
│       │   └── event_cache.py                      # v1 read-side addition if cache is split
│       └── tools/
│           ├── __init__.py
│           ├── commands.py
│           ├── permissions.py
│           ├── setup_support.py
│           └── state.py                            # v1 read-side tool registration
└── tests/
    ├── __init__.py
    ├── conftest.py
    └── unit/
        ├── __init__.py
        ├── test_auth.py
        ├── adapters/
        │   ├── __init__.py
        │   ├── test_mqtt_adapter.py
        │   └── test_mqtt_subscription_adapter.py   # v1 read-side addition if separated
        ├── config/
        │   ├── __init__.py
        │   ├── test_loader.py
        │   ├── test_models.py
        │   └── test_validation.py
        ├── domain/
        │   ├── __init__.py
        │   ├── test_models.py
        │   └── test_safety.py
        ├── services/
        │   ├── __init__.py
        │   ├── test_clock_service.py
        │   ├── test_device_state_service.py        # v1 read-side addition
        │   └── test_event_cache.py                 # v1 read-side addition if cache is split
        └── tools/
            ├── __init__.py
            ├── test_commands.py
            ├── test_setup_support.py
            └── test_state.py                       # v1 read-side addition
```

### Architectural Boundaries

**API Boundaries:**
The external API boundary is FastMCP tool registration. Tools are registered only through `src/mqtt_mcp/tools/__init__.py::register_all()`. The server exposes MCP tools, not REST or GraphQL endpoints.

**Component Boundaries:**
Tool modules handle MCP argument intake, auth, permission checks, domain validation calls, safe error responses, and service invocation. Services handle command dispatch, read-side cache queries, and business semantics. Adapters handle MQTT publishing, subscription callbacks, and paho-mqtt details. Domain modules remain infrastructure-free.

**Service Boundaries:**
`ClockService` owns write-side command dispatch. A read-side `DeviceStateService` should own state/event/cache query behavior. An `EventCache` may be a service-local class or separate service module, but cache mutation must not live in tool handlers.

**Data Boundaries:**
No durable database exists in v1. MQTT command payloads cross the outbound adapter boundary. MQTT retained state and event payloads cross the inbound subscription boundary and are stored in bounded in-memory structures. Returned read-side tool responses may wrap original payloads with metadata, but must preserve device-originated payload fields.

### Requirements to Structure Mapping

**Feature Mapping:**

- FR-1 through FR-3 command tools: `tools/commands.py`, `services/clock_service.py`, `adapters/mqtt_adapter.py`, `domain/safety.py`, tests in `tests/unit/tools/` and `tests/unit/services/`.
- FR-4 contract synchronization: exact topic/payload tests in `tests/unit/services/test_clock_service.py` and read-side topic tests for new subscription behavior.
- FR-5 safety validation: `domain/safety.py`, `domain/exceptions.py`, tests in `tests/unit/domain/`.
- FR-6 tool authorization: `auth.py`, `tools/commands.py`, future `tools/state.py`, tests in `tests/unit/test_auth.py` and `tests/unit/tools/`.
- FR-7 MQTT configuration: `config/models.py`, `config/loader.py`, `.env.example`, tests in `tests/unit/config/`.
- FR-8 startup preflight: `config/validation.py`, `server.py`, `tools/setup_support.py`, tests in `tests/unit/config/` and `tests/unit/tools/`.
- FR-9 through FR-12 read-side visibility: `adapters/mqtt_subscription_adapter.py` or `adapters/mqtt_adapter.py`, `services/device_state_service.py`, `services/event_cache.py`, `tools/state.py`, and matching unit tests.

**Cross-Cutting Concerns:**

- Tool registration: `tools/__init__.py` and `config/models.py::KNOWN_TOOL_NAMES`
- Auth/device scopes: `auth.py` and tool modules
- Validation: `domain/safety.py`
- Logging: `logging.py` and layer-local loggers
- Quality gates: `Makefile`, `pyproject.toml`, and tests

### Integration Points

**Internal Communication:**
`server.py` creates validated config and MQTT adapters, then calls `register_all()`. `register_all()` constructs services and passes them into tool registration functions. Tool handlers call services. Services call adapters. Adapters call paho-mqtt.

**External Integrations:**

- MCP clients call FastMCP tools.
- MQTT broker receives command publishes and provides retained state/events.
- `clock-server` remains the source of truth for MQTT topic and payload contracts.

**Data Flow:**
Write side: MCP tool -> auth/permission/validation -> `ClockService` -> MQTT adapter -> broker -> clock device.

Read side: broker -> MQTT subscription adapter/callback -> topic parser -> cache service -> MCP read tool -> agent.

### File Organization Patterns

**Configuration Files:**
Runtime config lives in `.env` locally, `.env.example` as the committed template, and Pydantic models under `src/mqtt_mcp/config/`. Project tooling config lives in `pyproject.toml`, `Makefile`, `Dockerfile`, and `uv.lock`.

**Source Organization:**
Source code stays under `src/mqtt_mcp/` and follows the existing architecture layers. New modules should be added only when they preserve a boundary or avoid mixing read-side and write-side responsibilities.

**Test Organization:**
Unit tests mirror source layers under `tests/unit/`. Contract-sensitive behavior requires exact assertions for topic strings, payload field names, and tool names.

**Asset Organization:**
No static assets are required for v1.

### Development Workflow Integration

**Development Server Structure:**
The package entrypoint remains `src/mqtt_mcp/__main__.py`; application assembly remains `src/mqtt_mcp/server.py::create_server()`.

**Build Process Structure:**
`uv_build` builds the package from `pyproject.toml`. Build artifacts belong in `dist/` and are not architecture inputs.

**Deployment Structure:**
The server can run as a local Python package command or containerized through the existing `Dockerfile`. Deployment configuration must come from environment variables, not hardcoded broker URLs, credentials, tokens, or device IDs.

## Architecture Validation Results

### Coherence Validation ✅

**Decision Compatibility:**
The architecture decisions are compatible. FastMCP remains the MCP surface, paho-mqtt remains isolated behind adapters, Pydantic v2 remains the configuration layer, and the read-side feature set fits the existing hexagonal structure. No decision requires a database, frontend, REST API, or additional MQTT client library.

**Pattern Consistency:**
The implementation patterns support the decisions. Naming rules align with Python conventions and the existing MCP tool surface. Error response rules preserve the current safe error shape. MQTT topic and payload rules preserve the `clock-server` contract. Read-side cache rules keep state mutation out of tool handlers.

**Structure Alignment:**
The project structure supports the architecture. Existing files remain the source of truth for command dispatch, config, auth, server composition, and tool registration. Proposed read-side files are placed in the same layer boundaries: adapter for MQTT ingestion, service/cache for state behavior, and tools for MCP handlers.

### Requirements Coverage Validation ✅

**Epic/Feature Coverage:**
No epics were loaded. Feature coverage was validated against the PRD functional requirement categories.

**Functional Requirements Coverage:**
All 12 PRD functional requirements are architecturally supported:

- FR-1 through FR-3 are covered by the existing command tool, service, adapter, safety, and tests structure.
- FR-4 is covered by contract synchronization rules and exact topic/payload testing expectations.
- FR-5 is covered by mandatory use of `domain/safety.py`.
- FR-6 is covered by static auth and device-scope authorization rules for all device-scoped tools.
- FR-7 is covered by Pydantic config models, environment loading, and `.env.example`.
- FR-8 is covered by preflight validation and known tool registration requirements.
- FR-9 through FR-12 are covered by the read-side subscription, bounded cache, state/event query tools, and contract fidelity decisions.

**Non-Functional Requirements Coverage:**
Safety, security, maintainability, contract fidelity, and local operability are addressed. Performance is addressed at v1 scale through bounded in-memory caches and no durable telemetry storage. Compliance requirements were not identified in the PRD.

### Implementation Readiness Validation ✅

**Decision Completeness:**
Critical implementation decisions are documented: existing repo foundation, MCP surface, MQTT adapter isolation, in-memory read-side data model, auth behavior, error handling, and quality gates.

**Structure Completeness:**
The structure is complete for current code and expected v1 additions. Proposed files are specific and mapped to requirements.

**Pattern Completeness:**
Conflict points that could cause AI agent divergence are covered: naming, module placement, tool registration, response formats, topic parsing, cache behavior, validation order, and tests.

### Gap Analysis Results

**Critical Gaps:**
None.

**Important Gaps:**
None blocking implementation.

**Minor Gaps:**
Freshness/staleness thresholds are not fully specified. This is acceptable for MVP because the architecture already says to report missing state as unavailable or unknown and to use `stale` only after a configured freshness threshold exists.

### Validation Issues Addressed

The validation identified no contradictions or blocking issues. The only minor gap, stale-state policy, is explicitly deferred until a concrete freshness threshold is introduced.

### Architecture Completeness Checklist

**Requirements Analysis**

- [x] Project context thoroughly analyzed
- [x] Scale and complexity assessed
- [x] Technical constraints identified
- [x] Cross-cutting concerns mapped

**Architectural Decisions**

- [x] Critical decisions documented with versions
- [x] Technology stack fully specified
- [x] Integration patterns defined
- [x] Performance considerations addressed

**Implementation Patterns**

- [x] Naming conventions established
- [x] Structure patterns defined
- [x] Communication patterns specified
- [x] Process patterns documented

**Project Structure**

- [x] Complete directory structure defined
- [x] Component boundaries established
- [x] Integration points mapped
- [x] Requirements to structure mapping complete

### Architecture Readiness Assessment

**Overall Status:** READY FOR IMPLEMENTATION

**Confidence Level:** high

**Key Strengths:**

- Strong alignment with the existing hexagonal codebase
- Clear safety and auth rules for all device-scoped tools
- Explicit separation between MQTT publish success and device acknowledgement
- Bounded in-memory read-side model avoids premature persistence
- Concrete file and test mapping for every PRD feature category

**Areas for Future Enhancement:**

- Configurable event cache bounds if defaults prove insufficient
- Configurable freshness thresholds for stale state
- Durable telemetry storage only if future requirements move beyond MVP visibility
- Device discovery only if future product scope changes

### Implementation Handoff

**AI Agent Guidelines:**

- Follow all architectural decisions exactly as documented.
- Use implementation patterns consistently across all components.
- Respect project structure and boundaries.
- Refer to this document for all architectural questions.
- Verify MQTT contract details against `clock-server` before changing topic or payload behavior.

**First Implementation Priority:**
Implement the read-side observation foundation: topic parsing, bounded event/state cache, and service-level query behavior, with unit tests before registering MCP read tools.
