"""Tests for domain safety rules."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from mqtt_mcp.domain.exceptions import (
    BrightnessOutOfRangeError,
    DurationOutOfRangeError,
    EmptyMessageError,
    InvalidAlarmTimeError,
    InvalidDeviceIdError,
    PastAlarmTimeError,
)
from mqtt_mcp.domain.safety import (
    check_brightness_level,
    check_duration,
    check_message,
    validate_alarm_time,
    validate_device_id,
)


class TestCheckBrightnessLevel:
    """Brightness must be 0-100."""

    def test_valid_levels(self) -> None:  # noqa: D102
        assert check_brightness_level(0) == 0
        assert check_brightness_level(50) == 50
        assert check_brightness_level(100) == 100

    def test_below_zero_raises(self) -> None:  # noqa: D102
        with pytest.raises(BrightnessOutOfRangeError):
            check_brightness_level(-1)

    def test_above_one_hundred_raises(self) -> None:  # noqa: D102
        with pytest.raises(BrightnessOutOfRangeError):
            check_brightness_level(101)

    def test_error_contains_field_suggestion(self) -> None:  # noqa: D102
        with pytest.raises(BrightnessOutOfRangeError) as exc:
            check_brightness_level(150)
        assert exc.value.field == "level"
        assert exc.value.suggestion is not None


class TestValidateAlarmTime:
    """Alarm time must be future UTC."""

    def test_future_time_passes(self) -> None:  # noqa: D102
        future = datetime.now(UTC) + timedelta(hours=1)
        result = validate_alarm_time(future)
        assert result == future

    def test_recent_past_raises(self) -> None:  # noqa: D102
        recent = datetime.now(UTC) - timedelta(seconds=30)
        with pytest.raises(PastAlarmTimeError):
            validate_alarm_time(recent)

    def test_past_beyond_grace_period_raises(self) -> None:  # noqa: D102
        past = datetime.now(UTC) - timedelta(minutes=5)
        with pytest.raises(PastAlarmTimeError):
            validate_alarm_time(past)

    def test_naive_datetime_raises(self) -> None:  # noqa: D102
        naive = datetime(2030, 1, 1, 7, 0, 0)
        with pytest.raises(InvalidAlarmTimeError):
            validate_alarm_time(naive)


class TestCheckMessage:
    """Message must be non-empty after trimming."""

    def test_valid_message(self) -> None:  # noqa: D102
        assert check_message("Hello") == "Hello"

    def test_message_with_whitespace(self) -> None:  # noqa: D102
        assert check_message("  Hello World  ") == "Hello World"

    def test_empty_message_raises(self) -> None:  # noqa: D102
        with pytest.raises(EmptyMessageError):
            check_message("")

    def test_whitespace_only_raises(self) -> None:  # noqa: D102
        with pytest.raises(EmptyMessageError):
            check_message("   ")


class TestCheckDuration:
    """Duration must be 1-3600."""

    def test_valid_durations(self) -> None:  # noqa: D102
        assert check_duration(1) == 1
        assert check_duration(1800) == 1800
        assert check_duration(3600) == 3600

    def test_below_minimum_raises(self) -> None:  # noqa: D102
        with pytest.raises(DurationOutOfRangeError):
            check_duration(0)

    def test_above_maximum_raises(self) -> None:  # noqa: D102
        with pytest.raises(DurationOutOfRangeError):
            check_duration(3601)


class TestValidateDeviceId:
    """Device ID must match ^[a-zA-Z0-9_-]{1,64}$."""

    def test_valid_device_ids(self) -> None:  # noqa: D102
        assert validate_device_id("clock-1") == "clock-1"
        assert validate_device_id("clock_kitchen") == "clock_kitchen"
        assert validate_device_id("a") == "a"
        assert validate_device_id("a" * 64) == "a" * 64

    def test_invalid_device_ids(self) -> None:  # noqa: D102
        with pytest.raises(InvalidDeviceIdError):
            validate_device_id("")
        with pytest.raises(InvalidDeviceIdError):
            validate_device_id("clock/1")
        with pytest.raises(InvalidDeviceIdError):
            validate_device_id("clock.1")
        with pytest.raises(InvalidDeviceIdError):
            validate_device_id("a" * 65)

    def test_error_contains_field_and_suggestion(self) -> None:  # noqa: D102
        with pytest.raises(InvalidDeviceIdError) as exc:
            validate_device_id("bad/id")
        assert exc.value.field == "deviceId"
        assert exc.value.suggestion is not None
