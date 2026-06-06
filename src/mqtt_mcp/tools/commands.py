"""MCP command tools — set_alarm, display_message, set_brightness.

Each tool validates inputs through domain safety, checks auth,
dispatches via ClockService, and returns structured results.
"""

from __future__ import annotations

import logging
from datetime import datetime

from mcp.server.fastmcp import FastMCP

from mqtt_mcp.config.models import AuthMode, MqttConfig
from mqtt_mcp.domain.exceptions import DomainError
from mqtt_mcp.domain.safety import (
    assert_tool_permitted,
    check_brightness_level,
    check_duration,
    check_message,
    validate_alarm_time,
    validate_device_id,
)
from mqtt_mcp.services.clock_service import ClockService

logger = logging.getLogger("mqtt_mcp")

# Module-level state set by register_commands()
_clock_service: ClockService | None = None
_config: MqttConfig | None = None


def _get_clock_service() -> ClockService:
    """Get the clock service, raising if not initialized."""
    if _clock_service is None:
        raise RuntimeError("Clock service not initialized")
    return _clock_service


def _authenticate(token: str | None) -> None:
    """Verify bearer token if auth is enabled."""
    from mqtt_mcp.auth import verify_token
    from mqtt_mcp.config.validation import get_credentials
    from mqtt_mcp.domain.exceptions import Unauthorized

    if _config is None or _config.auth_mode == AuthMode.NONE:
        return

    if not token:
        raise Unauthorized("Missing bearer token")

    creds = get_credentials()
    verify_token(token, creds)


def _safe_error(exc: DomainError) -> dict[str, object]:
    """Convert a DomainError to a safe response dict."""
    return {
        "error": str(exc),
        "category": exc.category.value,
        "field": exc.field,
        "suggestion": exc.suggestion,
    }


def register_commands(
    app: FastMCP,
    config: MqttConfig,
    clock_service: ClockService,
) -> None:
    """Register set_alarm, display_message, and set_brightness tools."""
    global _clock_service, _config
    _clock_service = clock_service
    _config = config

    @app.tool(name="set_alarm")
    def set_alarm(
        device_id: str,
        alarm_time: str,
        label: str | None = None,
        token: str | None = None,
    ) -> dict[str, object]:
        """Set an alarm on a smart clock device."""
        assert_tool_permitted("set_alarm")
        _authenticate(token)

        try:
            validate_device_id(device_id)
            parsed_time = _parse_rfc3339(alarm_time)
            validate_alarm_time(parsed_time)

            result = _get_clock_service().dispatch_command(
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
        _authenticate(token)

        try:
            validate_device_id(device_id)
            check_message(message)
            check_duration(duration_seconds)

            result = _get_clock_service().dispatch_command(
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
        _authenticate(token)

        try:
            validate_device_id(device_id)
            check_brightness_level(level)

            result = _get_clock_service().dispatch_command(
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


def _parse_rfc3339(value: str) -> datetime:
    """Parse an RFC3339 datetime string."""
    return datetime.fromisoformat(value.replace("Z", "+00:00"))
