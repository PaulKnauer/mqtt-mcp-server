"""Domain safety rule evaluation for MQTT MCP server.

Rules are transport-agnostic and reusable by all tool handlers.
No MQTT or infrastructure calls are made here.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime

from mqtt_mcp.domain.exceptions import (
    BrightnessOutOfRange,
    DurationOutOfRange,
    EmptyMessage,
    InvalidDeviceId,
    PastAlarmTime,
)

# Device ID pattern matching clock-server's contract:
# ^[a-zA-Z0-9_-]{1,64}$
_DEVICE_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]{1,64}$")


def check_brightness_level(level: int) -> int:
    """Validate and return a safe brightness level.

    Args:
        level: Target brightness (0-100).

    Returns:
        The brightness level if valid.

    Raises:
        BrightnessOutOfRange: if level is outside 0-100.
    """
    if not (0 <= level <= 100):
        raise BrightnessOutOfRange(level)
    return level


def validate_alarm_time(alarm_time: datetime) -> datetime:
    """Validate that an alarm time is in the future.

    Args:
        alarm_time: The proposed alarm time (must be timezone-aware UTC).

    Returns:
        The alarm time if valid.

    Raises:
        PastAlarmTime: if alarm_time is more than 1 minute in the past.
            A 1-minute grace period allows for clock skew.
    """
    now = datetime.now(UTC)
    if alarm_time.tzinfo is None:
        alarm_time = alarm_time.replace(tzinfo=UTC)
    # Allow up to 1 minute in the past for clock skew
    grace_period = 60.0
    if alarm_time.timestamp() < now.timestamp() - grace_period:
        raise PastAlarmTime(alarm_time.isoformat())
    return alarm_time


def check_message(message: str) -> str:
    """Validate that a message is non-empty after trimming.

    Args:
        message: The message text.

    Returns:
        The trimmed message if valid.

    Raises:
        EmptyMessage: if message is empty or whitespace only.
    """
    stripped = message.strip()
    if not stripped:
        raise EmptyMessage()
    return stripped


def check_duration(duration_seconds: int) -> int:
    """Validate that a duration is within acceptable range.

    Args:
        duration_seconds: Display duration in seconds.

    Returns:
        The duration if valid.

    Raises:
        DurationOutOfRange: if duration is outside 1-3600.
    """
    if not (1 <= duration_seconds <= 3600):
        raise DurationOutOfRange(duration_seconds)
    return duration_seconds


def validate_device_id(device_id: str) -> str:
    """Validate a device ID format.

    Args:
        device_id: The device identifier.

    Returns:
        The device ID if valid.

    Raises:
        InvalidDeviceId: if device_id doesn't match ^[a-zA-Z0-9_-]{1,64}$.
    """
    if not _DEVICE_ID_PATTERN.match(device_id):
        raise InvalidDeviceId(device_id)
    return device_id
