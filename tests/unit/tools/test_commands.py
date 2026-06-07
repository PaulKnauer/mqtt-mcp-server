"""Tests for command tools (set_alarm, display_message, set_brightness)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from mqtt_mcp.config.models import MqttConfig
from mqtt_mcp.services.clock_service import ClockService
from mqtt_mcp.tools.commands import register_commands


@pytest.fixture
def config() -> MqttConfig:  # noqa: D103
    return MqttConfig(broker_url="mqtt://localhost:1883")


@pytest.fixture
def service(config: MqttConfig) -> ClockService:  # noqa: D103
    adapter = MagicMock()
    return ClockService(adapter, config)


def _get_tool(app, name):
    """Get a registered tool by name."""
    tool = app._tool_manager.get_tool(name)
    assert tool is not None, f"Tool '{name}' not found"
    return tool


@pytest.fixture
def tools(config: MqttConfig, service: ClockService):
    """Register commands and return dict of tool name -> tool."""
    from mcp.server.fastmcp import FastMCP

    app = FastMCP("test")
    register_commands(app, config, service)

    names = ["set_alarm", "display_message", "set_brightness"]
    return {name: _get_tool(app, name) for name in names}


class TestSetAlarm:
    """set_alarm tool validations and dispatch."""

    def test_set_alarm_dispatches_correctly(self, tools: dict) -> None:  # noqa: D102
        result = tools["set_alarm"].fn(
            device_id="clock-1",
            alarm_time="2030-01-01T07:00:00Z",
        )
        assert result == {"result": "scheduled"}

    def test_set_alarm_with_label(self, tools: dict) -> None:  # noqa: D102
        result = tools["set_alarm"].fn(
            device_id="clock-1",
            alarm_time="2030-01-01T07:00:00Z",
            label="wake up",
        )
        assert result == {"result": "scheduled"}

    def test_set_alarm_invalid_device_id(self, tools: dict) -> None:  # noqa: D102
        result = tools["set_alarm"].fn(
            device_id="bad/id",
            alarm_time="2030-01-01T07:00:00Z",
        )
        assert "error" in result
        assert result["field"] == "deviceId"

    def test_set_alarm_past_time(self, tools: dict) -> None:  # noqa: D102
        result = tools["set_alarm"].fn(
            device_id="clock-1",
            alarm_time="2020-01-01T07:00:00Z",
        )
        assert "error" in result
        assert result["field"] == "alarmTime"


class TestDisplayMessage:
    """display_message tool validations and dispatch."""

    def test_display_message_dispatches(self, tools: dict) -> None:  # noqa: D102
        result = tools["display_message"].fn(
            device_id="clock-1",
            message="Meeting in 5 minutes",
            duration_seconds=30,
        )
        assert result == {"result": "sent"}

    def test_display_message_empty(self, tools: dict) -> None:  # noqa: D102
        result = tools["display_message"].fn(
            device_id="clock-1",
            message="",
            duration_seconds=30,
        )
        assert "error" in result
        assert result["field"] == "message"

    def test_display_message_bad_duration(self, tools: dict) -> None:  # noqa: D102
        result = tools["display_message"].fn(
            device_id="clock-1",
            message="Hi",
            duration_seconds=9999,
        )
        assert "error" in result
        assert result["field"] == "durationSeconds"


class TestSetBrightness:
    """set_brightness tool validations and dispatch."""

    def test_set_brightness_dispatches(self, tools: dict) -> None:  # noqa: D102
        result = tools["set_brightness"].fn(
            device_id="clock-1",
            level=75,
        )
        assert result == {"result": "updated"}

    def test_set_brightness_too_high(self, tools: dict) -> None:  # noqa: D102
        result = tools["set_brightness"].fn(
            device_id="clock-1",
            level=150,
        )
        assert "error" in result
        assert result["field"] == "level"
        assert "0" in str(result.get("suggestion", ""))
        assert "100" in str(result.get("suggestion", ""))

    def test_set_brightness_negative(self, tools: dict) -> None:  # noqa: D102
        result = tools["set_brightness"].fn(
            device_id="clock-1",
            level=-1,
        )
        assert "error" in result
        assert result["field"] == "level"
