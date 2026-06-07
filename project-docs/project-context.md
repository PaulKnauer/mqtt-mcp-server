---
project_name: "mqtt-mcp-server"
user_name: "Paul"
date: "2026-06-07"
sections_completed: ["discovery", "technology_stack", "language_specific_rules", "framework_specific_rules", "testing_rules", "code_quality_style_rules", "development_workflow_rules", "critical_dont_miss_rules"]
existing_patterns_found: 18
status: "complete"
rule_count: 55
optimized_for_llm: true
---

# Project Context for AI Agents

_This file contains critical rules and patterns that AI agents must follow when implementing code in this project. Focus on unobvious details that agents might otherwise miss._

---

## Technology Stack & Versions

- Runtime is Python `>=3.12`; use modern Python typing syntax and keep new code fully typed.
- MCP server surface uses FastMCP from `mcp[cli] >=1.26.0,<2.0.0`; register tools through the existing FastMCP registration flow.
- MQTT publishing goes through `paho-mqtt >=2.0.0,<3.0.0` wrapped by `src/mqtt_mcp/adapters/mqtt_adapter.py`; do not call paho directly outside the adapter.
- Runtime config uses Pydantic v2 (`pydantic >=2.0.0,<3.0.0`) and `SecretStr` for secrets.
- Environment loading uses `python-dotenv >=1.2.2,<2.0.0`; only `MQTT_MCP_*` variables are mapped into config.
- Use `uv` and the existing `Makefile` targets for install, test, lint, type-check, audit, build, and CI.

## Critical Implementation Rules

### Language-Specific Rules

- Add `from __future__ import annotations` to new Python modules unless there is a concrete reason not to.
- New functions and methods must be fully typed; `mypy` is configured with `disallow_untyped_defs = true` and `disallow_incomplete_defs = true`.
- Follow PEP 8 style and the repository's stricter ruff configuration; do not bypass lint failures with broad ignores.
- Keep domain models as frozen dataclasses in `src/mqtt_mcp/domain/models.py`; they must stay transport-agnostic and infrastructure-free.
- Use Pydantic v2 patterns for config models and validation; do not introduce Pydantic v1 APIs.
- Domain validation should raise typed `DomainError` subclasses, not return booleans, clamp values, or raise generic exceptions.
- Tool handlers should catch `DomainError` and return the existing safe error shape: `error`, `category`, `field`, and `suggestion`.
- Preserve Google-style docstrings where public classes, functions, or non-obvious behavior already use them.

### Framework-Specific Rules

- `src/mqtt_mcp/server.py::create_server()` is the single application composition root; instantiate and connect infrastructure there.
- Register every MCP tool through `src/mqtt_mcp/tools/__init__.py::register_all()`; do not register tools from scattered module side effects.
- Tool handlers must authenticate with `_authenticate(...)` before dispatching commands when device access is involved.
- Tool handlers may depend on services and config, but must not call MQTT adapters or paho-mqtt directly.
- Services own business dispatch behavior; `ClockService.dispatch_command()` constructs `{topic_prefix}/{device_id}/{command_type}` and publishes JSON payloads.
- Keep `MqttAdapter` as the only paho-mqtt wrapper; external MQTT library details should not leak into tools or domain code.
- Treat `~/github/clock-server` as the source repository for the MQTT topic and payload contract when contract details need verification.
- When adding a tool, update the handler, registration flow, permissions, config-known tool set if present, and unit tests together so preflight and permission checks remain consistent.

### Testing Rules

- Put unit tests under `tests/unit/<layer>/` matching the source layer: `domain`, `config`, `services`, `tools`, `adapters`.
- New or changed tool handlers need tests for success, domain validation failure, and auth/permission behavior when relevant.
- New or changed config/preflight behavior needs both success and failure tests; validation errors should preserve specific field context.
- Service dispatch tests must assert exact MQTT topic format and JSON payload shape, using a mocked adapter.
- Invalid device IDs must be tested as publish-blocking failures; adapter `publish` should not be called.
- MQTT command contract tests should be checked against `~/github/clock-server/internal/domain/command.go` and its tests before changing topic, command type, or payload field names.
- Keep coverage at or above the configured `fail_under = 70`; do not lower the coverage floor.
- Use `make test` for the pytest suite and `make coverage` when behavior or coverage-sensitive code changes.

### Code Quality & Style Rules

- Follow PEP 8 and enforce it through the repository's ruff configuration; run `make lint` before considering style complete.
- Keep line length at `100` characters unless ruff formatting chooses otherwise.
- Use ruff-managed import ordering; `mqtt_mcp` is configured as first-party.
- Keep formatting automated with `ruff format`; avoid manual style choices that fight the formatter.
- Use Google-style docstrings for public APIs and complex behavior; do not add noisy comments for obvious assignments or simple control flow.
- Keep names PEP 8 compliant: modules/functions/variables in `snake_case`, classes in `PascalCase`, constants in `UPPER_SNAKE_CASE`.
- Preserve layer-local file organization: domain logic in `domain`, config in `config`, MQTT wrapping in `adapters`, business dispatch in `services`, MCP handlers in `tools`.
- Do not add broad lint/type ignores; if an ignore is unavoidable, scope it narrowly and leave a concrete reason.

### Development Workflow Rules

- Use `make ci` as the full pre-merge quality gate: lint, type-check, coverage, audit, and build-check.
- Use focused gates while developing: `make lint`, `make type-check`, `make test`, `make coverage`, `make audit`, and `make build-check`.
- Do not lower coverage, mypy strictness, or ruff enforcement to make a change pass.
- Keep `.env` uncommitted; update `.env.example` when adding or changing supported configuration.
- New runtime config must be added consistently across defaults, env loading, Pydantic model validation, preflight behavior, docs, and tests.
- Secret config values must use `SecretStr`; never log or hardcode broker passwords, bearer tokens, device IDs, or broker URLs.
- If `make audit` changes, document any temporary vulnerability ignore in the Makefile with the CVE/advisory, impact, and revisit condition.

### Critical Don't-Miss Rules

- All safety validation must go through `src/mqtt_mcp/domain/safety.py`: `validate_device_id`, `validate_alarm_time`, `check_message`, `check_duration`, and `check_brightness_level`.
- Never silently clamp, coerce, or ignore invalid user input; raise or return the existing typed domain validation errors.
- Validate device IDs before constructing MQTT topics. This prevents topic injection through `/`, `+`, `#`, path traversal, spaces, and overlong IDs.
- Preserve the command payload contract: every MQTT command payload includes `deviceId`, `type`, and command-specific camelCase fields expected by `clock-server` and firmware.
- Verify contract changes against `~/github/clock-server/internal/domain/command.go` and related tests before changing command names, payload fields, or validation bounds.
- Auth mode `none` skips checks; auth mode `static` requires a valid token and device-scope authorization before dispatch.
- Token verification must use `hmac.compare_digest`; do not replace it with normal string equality.
- Device scopes must continue to support wildcard `*`, prefix wildcard such as `clock-*`, and exact matches such as `clock-1`.
- Config validation errors should surface the specific field or auth credential problem; avoid generic "validation failed" responses.
- Do not hardcode broker URLs, credentials, auth tokens, topic prefixes, or device IDs in source code.

---

## Usage Guidelines

**For AI Agents:**

- Read this file before implementing any code in this repository.
- Follow all rules exactly as documented; when in doubt, prefer the more restrictive project rule.
- Verify MQTT command contract changes against `~/github/clock-server` before editing topic or payload behavior.
- Update this file when new non-obvious implementation patterns become project standards.

**For Humans:**

- Keep this file lean and focused on rules agents are likely to miss.
- Update it when the technology stack, MQTT contract, auth model, or quality gates change.
- Review periodically for stale rules, redundant guidance, or patterns that have become obvious from code.

Last Updated: 2026-06-07
