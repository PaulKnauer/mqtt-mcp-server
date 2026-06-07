# Reconciliation — clock-server Contract

## Sources

- `~/github/clock-server/internal/domain/command.go`
- `~/github/clock-server/internal/adapters/mqtt/sender.go`
- `~/github/clock-server/docs/lcd-reference.md`

## Verdict

The PRD is aligned with the current `clock-server` command contract and the LCD reference's
read-side topic contract.

## Covered Inputs

- Command topics use `{topicPrefix}/{deviceId}/{commandType}`.
- Command types are `set_alarm`, `display_message`, and `set_brightness`.
- MQTT command payloads include `deviceId`, `type`, and command-specific camelCase fields.
- `set_alarm` includes `alarmTime` and `label`; empty labels are represented as an empty string.
- `display_message` includes `message` and `durationSeconds`.
- `set_brightness` includes `level`.
- Read-side v1 scope now covers:
  - `clocks/state/{deviceId}/presence`
  - `clocks/state/{deviceId}/display`
  - `clocks/state/{deviceId}/alarm`
  - `clocks/events/{deviceId}/heartbeat`
  - `clocks/events/{deviceId}/alarm_triggered`
  - `clocks/events/{deviceId}/alarm_acknowledged`
  - `clocks/events/{deviceId}/command_result`

## Gaps

- The current `mqtt-mcp-server` tests appear stricter than the PRD on alarm time offsets.
  Implementation work should reconcile tests/code with the PRD decision to accept RFC3339 values
  while still rejecting malformed or unsafe past times.
- The current `mqtt-mcp-server` implementation appears to expose command tools only. Read-side
  tools are therefore new v1 implementation scope, not already-complete functionality.
