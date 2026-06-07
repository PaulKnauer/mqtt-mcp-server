"""
MCP command tools — set_alarm, display_message, set_brightness.

Each tool validates inputs through domain safety, checks auth,
dispatches via ClockService, and returns structured results.
"""

from __future__ import annotations

import logging
from datetime import datetime

from mcp.server.fastmcp import FastMCP

from mqtt_mcp.config.models import AuthMode, MqttConfig
from mqtt_mcp.domain.exceptions import (
    DomainError,
    InvalidAlarmTimeError,
    MqttMCPError,
    UnauthorizedError,
)
from mqtt_mcp.domain.safety import (
    check_brightness_level,
    check_duration,
    check_message,
    validate_alarm_time,
    validate_device_id,
)
from mqtt_mcp.services.clock_service import ClockService
from mqtt_mcp.tools.permissions import assert_tool_permitted

logger = logging.getLogger("mqtt_mcp")


def _authenticate(config: MqttConfig, token: str | None, device_id: str | None) -> None:
    """
    Verify bearer token and device scope if auth is enabled.

    Performs constant-time token comparison and device-scope matching.
    Skips all checks when auth_mode is ``none``.

    Args:
        config: Server config (contains auth mode and credential info).
        token: Bearer token from the request, or ``None``.
        device_id: Target device ID for scope enforcement, or ``None``.

    Raises:
        UnauthorizedError: if token is missing or invalid.
        ForbiddenDeviceError: if token is valid but scope doesn't cover the device.

    """
    from mqtt_mcp.auth import check_device_authorization, verify_token
    from mqtt_mcp.config.validation import get_credentials

    if config.auth_mode == AuthMode.NONE:
        return

    if not token:
        raise UnauthorizedError("Missing bearer token")

    creds = get_credentials()
    # verify_token raises UnauthorizedError on mismatch (constant-time comparison)
    matched_cred = verify_token(token, creds)

    # Enforce device-scope authorization
    if device_id is not None:
        check_device_authorization(matched_cred, device_id)


def _safe_error(exc: MqttMCPError) -> dict[str, object]:
    """Convert an application error to a safe response dict."""
    payload: dict[str, object] = {
        "error": str(exc),
        "category": exc.category.value,
    }
    if isinstance(exc, DomainError):
        payload["field"] = exc.field
        payload["suggestion"] = exc.suggestion
    return payload


def _parse_rfc3339(value: str) -> datetime | None:
    """
    Parse an RFC3339 datetime string, returning None on invalid input.

    Only accepts full datetime strings (date + time + explicit UTC timezone).
    Rejects bare dates, timezone-less values, non-UTC timezones, and unparseable input.
    """
    try:
        normalised = value.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(normalised)
    except (ValueError, TypeError):
        return None

    # Reject date-only strings (no T separator means no time component)
    if "T" not in value:
        return None

    utc_offset = parsed.utcoffset()
    if parsed.tzinfo is None or utc_offset is None or utc_offset.total_seconds() != 0:
        return None

    return parsed


def register_commands(
    app: FastMCP,
    config: MqttConfig,
    clock_service: ClockService,
) -> None:
    """
    Register set_alarm, display_message, and set_brightness tools.

    Each tool handler captures ``config`` and ``clock_service`` in its
    closure — no module-level globals are used.

    Args:
        app: The FastMCP application.
        config: Server configuration.
        clock_service: Service for dispatching MQTT commands.

    """

    @app.tool(name="set_alarm")
    def set_alarm(
        device_id: str,
        alarm_time: str,
        label: str | None = None,
        token: str | None = None,
    ) -> dict[str, object]:
        """Set an alarm on a smart clock device."""
        try:
            assert_tool_permitted("set_alarm")
            validate_device_id(device_id)
            _authenticate(config, token, device_id)
            parsed_time = _parse_rfc3339(alarm_time)
            if parsed_time is None:
                raise InvalidAlarmTimeError(alarm_time)
            validate_alarm_time(parsed_time)

            result = clock_service.dispatch_command(
                device_id=device_id,
                command_type="set_alarm",
                payload={
                    "deviceId": device_id,
                    "type": "set_alarm",
                    "alarmTime": parsed_time.isoformat(),
                    "label": label,
                },
            )
            return dict(result)
        except MqttMCPError as exc:
            return _safe_error(exc)

    @app.tool(name="display_message")
    def display_message(
        device_id: str,
        message: str,
        duration_seconds: int,
        token: str | None = None,
    ) -> dict[str, object]:
        """Display a message on a smart clock device."""
        try:
            assert_tool_permitted("display_message")
            validate_device_id(device_id)
            safe_message = check_message(message)
            check_duration(duration_seconds)
            _authenticate(config, token, device_id)

            result = clock_service.dispatch_command(
                device_id=device_id,
                command_type="display_message",
                payload={
                    "deviceId": device_id,
                    "type": "display_message",
                    "message": safe_message,
                    "durationSeconds": duration_seconds,
                },
            )
            return dict(result)
        except MqttMCPError as exc:
            return _safe_error(exc)

    @app.tool(name="set_brightness")
    def set_brightness(
        device_id: str,
        level: int,
        token: str | None = None,
    ) -> dict[str, object]:
        """Set the screen brightness on a smart clock device."""
        try:
            assert_tool_permitted("set_brightness")
            validate_device_id(device_id)
            check_brightness_level(level)
            _authenticate(config, token, device_id)

            result = clock_service.dispatch_command(
                device_id=device_id,
                command_type="set_brightness",
                payload={
                    "deviceId": device_id,
                    "type": "set_brightness",
                    "level": level,
                },
            )
            return dict(result)
        except MqttMCPError as exc:
            return _safe_error(exc)
