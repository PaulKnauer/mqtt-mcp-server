"""Domain models for MQTT MCP server.

Frozen dataclasses representing smart clock command concepts.
These are transport-agnostic and shared across service and tool layers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class SetAlarmCommand:
    """Command to set an alarm on a smart clock device.

    Attributes:
        device_id: Target device identifier (e.g. "clock-1").
        alarm_time: The scheduled alarm time in UTC.
        label: Optional human-readable alarm label.
    """

    device_id: str
    alarm_time: datetime
    label: str | None = field(default=None)


@dataclass(frozen=True)
class DisplayMessageCommand:
    """Command to display a message on a smart clock device.

    Attributes:
        device_id: Target device identifier.
        message: The message text to display.
        duration_seconds: How long to display the message (1-3600).
    """

    device_id: str
    message: str
    duration_seconds: int


@dataclass(frozen=True)
class SetBrightnessCommand:
    """Command to set screen brightness on a smart clock device.

    Attributes:
        device_id: Target device identifier.
        level: Brightness level 0-100.
    """

    device_id: str
    level: int
