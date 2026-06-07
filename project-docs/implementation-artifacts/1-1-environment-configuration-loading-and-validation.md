---
baseline_commit: 0f9450a454375ef366b1452c6d2da4e2eec41575
---

# Story 1.1: Environment Configuration Loading and Validation

Status: done

<!-- Ultimate context engine analysis completed - comprehensive developer guide created -->

## Story

As a homelab user,
I want to configure MQTT and auth settings through environment variables,
so that I can run the MCP server without editing source code or exposing secrets.

## Acceptance Criteria

1. Given valid `MQTT_MCP_*` environment variables for broker connection, topic prefix, QoS, retained flag, and auth mode, when server configuration is loaded, then a validated `MqttConfig` is produced with expected field values and secret values are represented with secret-aware types.
2. Given an invalid configuration value, when configuration validation runs, then validation fails with an error that identifies the specific field and no generic-only "validation failed" message is returned.
3. Given source files in the repository, when configuration support is reviewed, then broker URLs, credentials, auth tokens, topic prefixes, and device IDs are not hardcoded in source code, and `.env.example` documents supported non-secret and secret configuration inputs without containing real secrets.

## Tasks / Subtasks

- [x] Complete config model support for all Story 1.1 fields (AC: 1, 2)
  - [x] Add a `retained: bool` field to `src/mqtt_mcp/config/models.py::MqttConfig` with a default of `False`.
  - [x] Preserve `SecretStr` for `broker_password` and `auth_token`; do not convert secrets to plain strings except at the adapter/auth boundary where needed.
  - [x] Keep `auth_mode` as the existing `AuthMode` enum with accepted values `none` and `static`.
  - [x] Ensure invalid `broker_url`, `topic_prefix`, `qos`, `retained`, `auth_mode`, and extra fields produce `pydantic.ValidationError` output containing the specific field name.
- [x] Wire retained-flag loading through every config entrypoint (AC: 1)
  - [x] Add `retained` to `src/mqtt_mcp/config/defaults.py::DEFAULTS`.
  - [x] Add `MQTT_MCP_RETAINED` to `src/mqtt_mcp/config/loader.py::_ENV_MAP`.
  - [x] Verify `.env` file values, process environment values, and `overrides` all support retained flag parsing through Pydantic.
- [x] Propagate retained behavior only through existing layers (AC: 1, 3)
  - [x] Update `src/mqtt_mcp/services/clock_service.py` to read `config.retained`.
  - [x] Update `src/mqtt_mcp/adapters/mqtt_adapter.py::publish` to accept a typed `retain: bool = False` parameter and pass it to paho `Client.publish`.
  - [x] Keep MQTT publishing behind `MqttAdapter`; tools must not call paho or adapter internals directly.
  - [x] Preserve exact command topic format `{topicPrefix}/{deviceId}/{commandType}` and existing payload serialization.
- [x] Update `.env.example` without adding real secrets (AC: 3)
  - [x] Document `MQTT_MCP_RETAINED=false`.
  - [x] Document `MQTT_MCP_AUTH_MODE=none` explicitly.
  - [x] Keep credential examples blank or placeholder-only; do not include real broker URLs, tokens, passwords, or device IDs.
- [x] Expand config tests around success and failure paths (AC: 1, 2, 3)
  - [x] Add model tests for default retained value, env/override parsing, and invalid retained values.
  - [x] Add loader tests for `MQTT_MCP_RETAINED`, `MQTT_MCP_AUTH_MODE`, broker credentials, and secret fields.
  - [x] Add validation tests that assert specific field names appear in validation errors.
  - [x] Add or update adapter/service tests asserting `retain=config.retained` is passed to paho publish.
  - [x] Add `.env.example` coverage or a focused source-text test that verifies documented supported env vars and absence of real secret values.
- [x] Run focused and full quality gates (AC: 1, 2, 3)
  - [x] Run `make lint`.
  - [x] Run `make type-check`.
  - [x] Run `make test`.
  - [x] Run `make coverage` if coverage-sensitive changes are made.
- [x] Review Follow-ups (AI)
  - [x] [AI-Review][medium] Ignore blank `MQTT_MCP_*` values in project-local `.env` consistently with process-environment handling so `MQTT_MCP_RETAINED=` falls back to defaults instead of failing validation. (AC: 1, 2)
  - [x] [AI-Review][low] Add loader-path tests proving `MQTT_MCP_BROKER_PASSWORD` and `MQTT_MCP_AUTH_TOKEN` remain secret-aware when loaded from environment sources. (AC: 1)

## Dev Notes

### Story Scope

This is config foundation work for Epic 1. Do not implement command tools, auth enforcement changes, startup preflight behavior, or read-side device state tools in this story. Those are covered by Stories 1.2, 1.3, Epic 2, and Epic 3.

The key missing Story 1.1 requirement in current code is retained-flag configuration. The PRD and epics require broker URL, credentials, topic prefix, QoS, retained flag, and auth mode to be environment-configurable. Current code supports all of those except retained command publishing. [Source: project-docs/planning-artifacts/epics.md#Story-1.1-Environment-Configuration-Loading-and-Validation] [Source: project-docs/planning-artifacts/prds/prd-mqtt-mcp-server-2026-06-07/prd.md#FR-7-MQTT-Configuration]

### Current State: Files To Update

- `src/mqtt_mcp/config/models.py`
  - Current `MqttConfig` fields: `broker_url`, `broker_username`, `broker_password`, `topic_prefix`, `qos`, `auth_mode`, `auth_token`, `auth_credentials`, and `log_level`.
  - Current secret-aware fields: `broker_password: SecretStr | None` and `auth_token: SecretStr | None`.
  - Current validators reject non-`mqtt://`/`mqtts://` broker URLs and empty topic prefixes.
  - Add only the retained config field needed by Story 1.1; do not add read-side cache, freshness, or subscription config here.

- `src/mqtt_mcp/config/defaults.py`
  - Current defaults include broker URL, credentials as `None`, `topic_prefix`, `qos`, auth settings, and log level.
  - Add retained default here so `load_config()` and direct model defaults stay aligned.

- `src/mqtt_mcp/config/loader.py`
  - Current resolution order is defaults, project-local `.env`, process environment, then overrides.
  - `_ENV_MAP` currently maps only `MQTT_MCP_BROKER_URL`, username/password, topic prefix, QoS, auth token/credentials/mode, and log level.
  - Add `MQTT_MCP_RETAINED` here; keep support limited to `MQTT_MCP_*` env vars.

- `src/mqtt_mcp/services/clock_service.py`
  - Current service validates Device ID before topic construction, builds `{topic_prefix}/{device_id}/{command_type}`, JSON-serializes the payload, and calls `adapter.publish(topic, json_payload, qos=self._qos)`.
  - Preserve Device ID validation before topic construction.
  - Add retained propagation by storing `config.retained` and passing `retain=self._retained` to the adapter publish call.

- `src/mqtt_mcp/adapters/mqtt_adapter.py`
  - Current `publish()` accepts `topic`, `payload`, and `qos`, then calls paho with `retain=False`.
  - Change the adapter method signature to include `retain: bool = False`, and pass that value to paho.
  - Do not expose paho details outside this adapter.

- `.env.example`
  - Current file documents broker URL, username/password, topic prefix, QoS, auth token/credentials, and log level.
  - It does not document retained flag or auth mode explicitly.
  - Add retained and auth mode examples with safe placeholder values only.

### Architecture Compliance

- Keep application composition in `src/mqtt_mcp/server.py::create_server()`. Story 1.1 should not move server assembly or tool registration.
- Keep config validation in `src/mqtt_mcp/config/models.py` and environment loading in `src/mqtt_mcp/config/loader.py`.
- Keep paho-mqtt behind `src/mqtt_mcp/adapters/mqtt_adapter.py`; services may call adapter methods, tools may not.
- Domain models remain frozen dataclasses and infrastructure-free; Story 1.1 should not require domain model changes.
- Do not hardcode broker URLs, credentials, auth tokens, topic prefixes, or device IDs in source code beyond safe defaults and placeholder examples.
- Preserve `KNOWN_TOOL_NAMES` as-is for this story; no new tools are introduced.

### Testing Requirements

Required focused tests:

- `tests/unit/config/test_models.py`
  - Default retained is `False`.
  - Valid retained values parse to bool through Pydantic.
  - Invalid field values produce errors containing field names such as `broker_url`, `qos`, `retained`, and `auth_mode`.
  - `broker_password` and `auth_token` remain `SecretStr`.

- `tests/unit/config/test_loader.py`
  - `MQTT_MCP_RETAINED` is read from process env and `.env`.
  - `MQTT_MCP_AUTH_MODE` is read from env.
  - Overrides still win over env vars.
  - Empty env vars remain ignored consistently with current behavior.

- `tests/unit/services/test_clock_service.py`
  - When `MqttConfig(retained=True)` is used, `ClockService.dispatch_command()` calls adapter publish with `retain=True`.
  - Existing topic and payload assertions remain exact.

- `tests/unit/adapters/test_mqtt_adapter.py`
  - Adapter publish passes `retain=True` to paho when requested.
  - Existing default behavior remains `retain=False`.

- Optional but useful: a config/docs test that reads `.env.example` and asserts the supported env vars are documented without real secret values.

Run at minimum: `make lint`, `make type-check`, and `make test`. Run `make coverage` if the new tests materially affect coverage reporting.

### Previous Story Intelligence

No previous story exists in Epic 1. There are no prior Story 1.x implementation notes to incorporate.

### Git Intelligence Summary

Recent history is planning-heavy plus one hardening pass:

- `0f9450a` added planning artifacts, sprint status, architecture, epics, PRD, and readiness report.
- `debbb3e` fixed adversarial review findings across config, auth, MQTT adapter, server, tools, and tests. Current patterns from that commit should be extended rather than replaced.
- `7037264` added `project-docs/project-context.md`, which is now foundational agent context.

Actionable takeaway: extend the existing config and adapter tests in-place. Do not introduce a new config subsystem or alternate MQTT library.

### Latest Technical Information

- Pydantic v2 field validators remain the right pattern for custom field validation; validators raise field-specific `ValidationError` entries, and `ValueError` is the standard exception inside validators. Source: https://pydantic.dev/docs/validation/latest/concepts/validators/
- Pydantic `SecretStr` is appropriate for secret values because nonempty secrets display as masked in `repr()`/`str()` while `get_secret_value()` exposes the underlying value only where explicitly needed. Source: https://pydantic.dev/docs/validation/latest/api/pydantic/types/#secretstr
- paho-mqtt `Client.publish` accepts `retain: bool = False`; setting it true makes the broker retain the message for the topic. Source: https://eclipse.dev/paho/files/paho.mqtt.python/html/client.html#paho.mqtt.client.Client.publish
- The official MCP Python SDK documents FastMCP as the server interface and current stable v1.x path; no MCP dependency or registration change is needed for this config story. Source: https://github.com/modelcontextprotocol/python-sdk
- `python-dotenv` 1.2.2 is the current dependency pinned by this repo and has a PyPI release uploaded on 2026-03-01. No dependency change is needed. Source: https://pypi.org/project/python-dotenv/

### Project Structure Notes

Expected touched files:

- `src/mqtt_mcp/config/models.py`
- `src/mqtt_mcp/config/defaults.py`
- `src/mqtt_mcp/config/loader.py`
- `src/mqtt_mcp/services/clock_service.py`
- `src/mqtt_mcp/adapters/mqtt_adapter.py`
- `.env.example`
- `tests/unit/config/test_models.py`
- `tests/unit/config/test_loader.py`
- `tests/unit/services/test_clock_service.py`
- `tests/unit/adapters/test_mqtt_adapter.py`

Do not touch:

- `src/mqtt_mcp/tools/__init__.py` or `KNOWN_TOOL_NAMES` unless a test exposes an existing issue unrelated to this story.
- `src/mqtt_mcp/domain/safety.py`; no new safety rule is required for retained config.
- `src/mqtt_mcp/auth.py`; Story 1.3 owns auth behavior beyond config loading.
- Read-side modules proposed in architecture; those belong to Epic 3.

### References

- [Source: project-docs/project-context.md#Technology-Stack--Versions]
- [Source: project-docs/project-context.md#Critical-Dont-Miss-Rules]
- [Source: project-docs/planning-artifacts/epics.md#Story-1.1-Environment-Configuration-Loading-and-Validation]
- [Source: project-docs/planning-artifacts/prds/prd-mqtt-mcp-server-2026-06-07/prd.md#FR-7-MQTT-Configuration]
- [Source: project-docs/planning-artifacts/architecture.md#Requirements-to-Structure-Mapping]
- [Source: src/mqtt_mcp/config/models.py]
- [Source: src/mqtt_mcp/config/loader.py]
- [Source: src/mqtt_mcp/config/defaults.py]
- [Source: src/mqtt_mcp/services/clock_service.py]
- [Source: src/mqtt_mcp/adapters/mqtt_adapter.py]
- [Source: .env.example]

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

- 2026-06-07: `uv run pytest -q tests/unit/config/test_loader.py` failed in red phase on empty `.env` handling, confirming blank dotenv values were being forwarded into `MqttConfig`.
- 2026-06-07: `make lint`, `make type-check`, `make test`, and `make coverage` all passed after fixing loader normalization and expanding loader coverage.

### Completion Notes List

- Added `retained: bool = False` field to `MqttConfig` using standard Pydantic v2 `Field`; validated via Pydantic's built-in bool coercion (strings "true"/"false" parse correctly from env vars).
- Added `"retained": False` to `DEFAULTS` and `"MQTT_MCP_RETAINED": "retained"` to `_ENV_MAP` so the retained flag flows through all resolution layers: defaults → .env → env vars → overrides.
- Updated `ClockService.__init__` to capture `self._retained = config.retained` and pass `retain=self._retained` to `adapter.publish()`, completing the config-to-wire propagation chain.
- Updated `MqttAdapter.publish` signature from `(topic, payload, qos)` to `(topic, payload, qos, retain=False)`, threading the caller-supplied flag through to paho `Client.publish`.
- Added 21 new tests across four test files; updated one existing assertion in `test_clock_service.py` to include `retain=False` in the expected mock call. All 134 tests pass, lint clean, mypy clean, coverage 89%.
- `.env.example` now explicitly documents `MQTT_MCP_RETAINED=false` and `MQTT_MCP_AUTH_MODE=none`.
- Normalized `_read_dotenv()` to ignore blank and whitespace-only supported values so project-local `.env` handling now matches process-environment behavior for all `MQTT_MCP_*` settings.
- Added loader-path coverage proving empty dotenv values fall back to defaults and that `MQTT_MCP_BROKER_PASSWORD` plus `MQTT_MCP_AUTH_TOKEN` still arrive as `SecretStr`.
- ✅ Resolved review finding [medium]: blank `MQTT_MCP_*` values in project-local `.env` are ignored consistently, preventing `MQTT_MCP_RETAINED=` from failing validation.
- ✅ Resolved review finding [low]: loader tests now verify secret-bearing env inputs stay secret-aware through `load_config()`.

### File List

- src/mqtt_mcp/config/models.py
- src/mqtt_mcp/config/defaults.py
- src/mqtt_mcp/config/loader.py
- src/mqtt_mcp/services/clock_service.py
- src/mqtt_mcp/adapters/mqtt_adapter.py
- .env.example
- tests/unit/config/test_models.py
- tests/unit/config/test_loader.py
- tests/unit/services/test_clock_service.py
- tests/unit/adapters/test_mqtt_adapter.py
- project-docs/implementation-artifacts/1-1-environment-configuration-loading-and-validation.md
- project-docs/implementation-artifacts/sprint-status.yaml

## Change Log

- 2026-06-07: Added `retained` bool field to `MqttConfig`, `DEFAULTS`, and `_ENV_MAP`; propagated retain flag through `ClockService` → `MqttAdapter` → paho; updated `.env.example`; added 21 new tests. Story 1.1 complete.
- 2026-06-07: Addressed code review findings for Story 1.1 by ignoring blank supported `.env` values in the loader and adding secret-field loader coverage.
