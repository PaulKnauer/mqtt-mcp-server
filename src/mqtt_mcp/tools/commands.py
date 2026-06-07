"""
MCP command tools — set_alarm, display_message, set_brightness.

Each tool validates inputs through domain safety, checks auth,
dispatches via ClockService, and returns structured results.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from mcp.server.fastmcp import FastMCP

from mqtt_mcp.config.models import AuthMode, MqttConfig
from mqtt_mcp.domain.exceptions import DomainError, UnauthorizedError
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


def _safe_error(exc: DomainError) -> dict[str, object]:
    """Convert a DomainError to a safe response dict."""
    return {
        "error": str(exc),
        "category": exc.category.value,
        "field": exc.field,
        "suggestion": exc.suggestion,
    }


def _parse_rfc3339(value: str) -> datetime | None:
    """
    Parse an RFC3339 datetime string, returning None on invalid input.

    Only accepts full datetime strings (date + time + UTC timezone).
    Rejects bare dates, non-UTC timezones, and unparseable input.
    """
    try:
        normalised = value.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(normalised)
    except (ValueError, TypeError):
        return None

    # Reject date-only strings (no T separator means no time component)
    if "T" not in value:
        return None

    # Normalise to UTC — reject non-UTC timezones
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    else:
        utc_offset = parsed.utcoffset()
        if utc_offset is None or utc_offset.total_seconds() != 0:
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
        assert_tool_permitted("set_alarm")
        _authenticate(config, token, device_id)

        try:
            validate_device_id(device_id)
            parsed_time = _parse_rfc3339(alarm_time)
            if parsed_time is None:
                return {"error": "Invalid alarm_time format; expected RFC3339 UTC"}
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
        except DomainError as exc:
            return _safe_error(exc)

    @app.tool(name="display_message")
    def display_message(
        device_id: str,
        message: str,
        duration_seconds: int,
        token: str | None = None,
    ) -> dict[str, object]:
        """Display a message on a smart clock device."""
        assert_tool_permitted("display_message")
        _authenticate(config, token, device_id)

        try:
            validate_device_id(device_id)
            check_message(message)
            check_duration(duration_seconds)

            result = clock_service.dispatch_command(
                device_id=device_id,
                command_type="display_message",
                payload={
                    "deviceId": device_id,
                    "type": "display_message",
                    "message": message,
                    "durationSeconds": duration_seconds,
                },
            )
            return dict(result)
        except DomainError as exc:
            return _safe_error(exc)

    @app.tool(name="set_brightness")
    def set_brightness(
        device_id: str,
        level: int,
        token: str | None = None,
    ) -> dict[str, object]:
        """Set the screen brightness on a smart clock device."""
        assert_tool_permitted("set_brightness")
        _authenticate(config, token, device_id)

        try:
            validate_device_id(device_id)
            check_brightness_level(level)

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
        except DomainError as exc:
            return _safe_error(exc)
