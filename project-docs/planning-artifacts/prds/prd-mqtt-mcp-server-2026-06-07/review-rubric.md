# PRD Quality Review — mqtt-mcp-server

## Overall verdict

The PRD is decision-ready for a homelab/hobby project. It has a clear thesis, grounded command
contract, and enough testable requirements to feed architecture and story creation. The main risk
is that the newly added read-side v1 scope needs a more explicit MCP tool surface and runtime
behavior before implementation planning.

## Decision-readiness — adequate

The PRD records the key product decisions: homelab scope, `clock-server` as source of truth,
RFC3339 alarm handling, empty alarm-label behavior, and read-side visibility in v1. The trade-off
around read-side storage is also named: v1 aims for latest state and bounded recent events, not
durable telemetry.

### Findings

- **medium** Read-side implementation boundary needs sharper wording (§4.4) — The PRD says the
  server "reads or maintains" snapshots, which leaves story creation with two materially different
  designs. *Fix:* state the expected v1 behavior as MQTT subscription plus in-memory latest-state
  and recent-event cache unless architecture later changes it.

## Substance over theater — strong

The PRD is lean and domain-specific. The journeys and glossary are not decorative; they support
the command and read-side requirements.

### Findings

- None.

## Strategic coherence — strong

The thesis is coherent: expose `clock-server` smart-clock control and visibility to AI agents
without creating a second contract. The feature set follows that thesis.

### Findings

- None.

## Done-ness clarity — adequate

Command FRs are testable and clear. Read-side FRs have concrete topics and payload expectations,
but the MCP tool names and runtime cache behavior should be explicit.

### Findings

- **high** Read-side MCP tools are unnamed (§4.4, §6.1) — Downstream stories need concrete tool
  names and expected return semantics. *Fix:* add tool names such as `get_device_state`,
  `get_recent_events`, and `get_command_results`, with unavailable-state behavior.

## Scope honesty — strong

Non-goals are explicit and useful. The PRD avoids public SaaS, dashboards, durable telemetry, and
device discovery.

### Findings

- None.

## Downstream usability — adequate

FR, UJ, and SM IDs are stable and mostly cross-linked. The assumptions section should be converted
to validated assumptions or removed before finalization, since the user resolved the main open
items.

### Findings

- **medium** Assumptions remain tagged after decisions were resolved (§9) — Final PRDs should not
  carry unresolved `[ASSUMPTION]` tags unless they are intentionally deferred. *Fix:* convert §9 to
  validated assumptions and constraints without bracket tags.

## Shape fit — strong

The PRD fits a hobby/developer/IoT integration product. It is specific enough for downstream work
without enterprise-process weight.

### Findings

- None.

## Mechanical notes

- IDs are contiguous: UJ-1 through UJ-4, FR-1 through FR-12, SM-1 through SM-5.
- No unresolved open questions remain.
- The PRD should update §8/§9 wording during polish so it reads as final rather than draft.
