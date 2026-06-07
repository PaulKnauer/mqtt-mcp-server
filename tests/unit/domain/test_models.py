"""Tests for domain models."""

from __future__ import annotations

import dataclasses
from datetime import UTC, datetime

import pytest

from mqtt_mcp.domain.models import (
    DisplayMessageCommand,
    SetAlarmCommand,
    SetBrightnessCommand,
)


class TestSetAlarmCommand:
    """SetAlarmCommand is a frozen dataclass."""

    def test_creates_command(self) -> None:  # noqa: D102
        alarm_time = datetime(2030, 1, 1, 7, 0, 0, tzinfo=UTC)
        cmd = SetAlarmCommand(device_id="clock-1", alarm_time=alarm_time, label="wake up")
        assert cmd.device_id == "clock-1"
        assert cmd.alarm_time == alarm_time
        assert cmd.label == "wake up"

    def test_default_label_is_none(self) -> None:  # noqa: D102
        alarm_time = datetime(2030, 1, 1, 7, 0, 0, tzinfo=UTC)
        cmd = SetAlarmCommand(device_id="clock-1", alarm_time=alarm_time)
        assert cmd.label is None

    def test_is_frozen(self) -> None:  # noqa: D102
        cmd = SetAlarmCommand(
            device_id="clock-1",
            alarm_time=datetime(2030, 1, 1, 7, 0, 0, tzinfo=UTC),
        )
        assert dataclasses.is_dataclass(cmd)
        with pytest.raises(dataclasses.FrozenInstanceError):
            cmd.device_id = "clock-2"  # type: ignore[misc]


class TestDisplayMessageCommand:
    """DisplayMessageCommand is a frozen dataclass."""

    def test_creates_command(self) -> None:  # noqa: D102
        cmd = DisplayMessageCommand(
            device_id="clock-1",
            message="Meeting in 5 minutes",
            duration_seconds=30,
        )
        assert cmd.device_id == "clock-1"
        assert cmd.message == "Meeting in 5 minutes"
        assert cmd.duration_seconds == 30

    def test_is_frozen(self) -> None:  # noqa: D102
        cmd = DisplayMessageCommand(device_id="clock-1", message="hi", duration_seconds=10)
        assert dataclasses.is_dataclass(cmd)
        with pytest.raises(dataclasses.FrozenInstanceError):
            cmd.message = "changed"  # type: ignore[misc]


class TestSetBrightnessCommand:
    """SetBrightnessCommand is a frozen dataclass."""

    def test_creates_command(self) -> None:  # noqa: D102
        cmd = SetBrightnessCommand(device_id="clock-1", level=75)
        assert cmd.device_id == "clock-1"
        assert cmd.level == 75

    def test_is_frozen(self) -> None:  # noqa: D102
        cmd = SetBrightnessCommand(device_id="clock-1", level=50)
        assert dataclasses.is_dataclass(cmd)
        with pytest.raises(dataclasses.FrozenInstanceError):
            cmd.level = 75  # type: ignore[misc]
