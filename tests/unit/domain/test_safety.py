"""Tests for domain safety rules."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from mqtt_mcp.domain.exceptions import (
    BrightnessOutOfRange,
    DurationOutOfRange,
    EmptyMessage,
    InvalidDeviceId,
    PastAlarmTime,
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

    def test_valid_levels(self) -> None:
        assert check_brightness_level(0) == 0
        assert check_brightness_level(50) == 50
        assert check_brightness_level(100) == 100

    def test_below_zero_raises(self) -> None:
        with pytest.raises(BrightnessOutOfRange):
            check_brightness_level(-1)

    def test_above_one_hundred_raises(self) -> None:
        with pytest.raises(BrightnessOutOfRange):
            check_brightness_level(101)

    def test_error_contains_field_suggestion(self) -> None:
        with pytest.raises(BrightnessOutOfRange) as exc:
            check_brightness_level(150)
        assert exc.value.field == "level"
        assert exc.value.suggestion is not None


class TestValidateAlarmTime:
    """Alarm time must not be more than 1 minute in the past."""

    def test_future_time_passes(self) -> None:
        future = datetime.now(UTC) + timedelta(hours=1)
        result = validate_alarm_time(future)
        assert result == future

    def test_recent_past_within_grace_period(self) -> None:
        recent = datetime.now(UTC) - timedelta(seconds=30)
        result = validate_alarm_time(recent)
        assert result == recent

    def test_past_beyond_grace_period_raises(self) -> None:
        past = datetime.now(UTC) - timedelta(minutes=5)
        with pytest.raises(PastAlarmTime):
            validate_alarm_time(past)

    def test_naive_datetime_gets_utc_assumed(self) -> None:
        naive = datetime(2030, 1, 1, 7, 0, 0)
        result = validate_alarm_time(naive)
        assert result.tzinfo is not None


class TestCheckMessage:
    """Message must be non-empty after trimming."""

    def test_valid_message(self) -> None:
        assert check_message("Hello") == "Hello"

    def test_message_with_whitespace(self) -> None:
        assert check_message("  Hello World  ") == "Hello World"

    def test_empty_message_raises(self) -> None:
        with pytest.raises(EmptyMessage):
            check_message("")

    def test_whitespace_only_raises(self) -> None:
        with pytest.raises(EmptyMessage):
            check_message("   ")


class TestCheckDuration:
    """Duration must be 1-3600."""

    def test_valid_durations(self) -> None:
        assert check_duration(1) == 1
        assert check_duration(1800) == 1800
        assert check_duration(3600) == 3600

    def test_below_minimum_raises(self) -> None:
        with pytest.raises(DurationOutOfRange):
            check_duration(0)

    def test_above_maximum_raises(self) -> None:
        with pytest.raises(DurationOutOfRange):
            check_duration(3601)


class TestValidateDeviceId:
    """Device ID must match ^[a-zA-Z0-9_-]{1,64}$."""

    def test_valid_device_ids(self) -> None:
        assert validate_device_id("clock-1") == "clock-1"
        assert validate_device_id("clock_kitchen") == "clock_kitchen"
        assert validate_device_id("a") == "a"
        assert validate_device_id("a" * 64) == "a" * 64

    def test_invalid_device_ids(self) -> None:
        with pytest.raises(InvalidDeviceId):
            validate_device_id("")
        with pytest.raises(InvalidDeviceId):
            validate_device_id("clock/1")
        with pytest.raises(InvalidDeviceId):
            validate_device_id("clock.1")
        with pytest.raises(InvalidDeviceId):
            validate_device_id("a" * 65)

    def test_error_contains_field_and_suggestion(self) -> None:
        with pytest.raises(InvalidDeviceId) as exc:
            validate_device_id("bad/id")
        assert exc.value.field == "deviceId"
        assert exc.value.suggestion is not None
