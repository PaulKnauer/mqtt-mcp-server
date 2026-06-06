"""Tests for the ClockService."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from mqtt_mcp.config.models import MqttConfig
from mqtt_mcp.domain.exceptions import DispatchError, InvalidDeviceId
from mqtt_mcp.services.clock_service import ClockService


@pytest.fixture
def config() -> MqttConfig:
    return MqttConfig(broker_url="mqtt://localhost:1883", topic_prefix="clocks/commands", qos=1)


@pytest.fixture
def adapter() -> MagicMock:
    return MagicMock()


@pytest.fixture
def service(config: MqttConfig, adapter: MagicMock) -> ClockService:
    return ClockService(adapter, config)


class TestClockServiceDispatch:
    """Dispatching commands via ClockService."""

    def test_dispatch_set_alarm(self, service: ClockService, adapter: MagicMock) -> None:
        result = service.dispatch_command(
            device_id="clock-1",
            command_type="set_alarm",
            payload={
                "deviceId": "clock-1",
                "type": "set_alarm",
                "alarmTime": "2030-01-01T07:00:00Z",
            },
        )
        assert result == {"result": "scheduled"}
        adapter.publish.assert_called_once_with(
            "clocks/commands/clock-1/set_alarm",
            '{"deviceId": "clock-1", "type": "set_alarm", "alarmTime": "2030-01-01T07:00:00Z"}',
            qos=1,
        )

    def test_dispatch_display_message(self, service: ClockService, adapter: MagicMock) -> None:
        result = service.dispatch_command(
            device_id="clock-1",
            command_type="display_message",
            payload={
                "deviceId": "clock-1",
                "type": "display_message",
                "message": "Hi",
                "durationSeconds": 30,
            },
        )
        assert result == {"result": "sent"}

    def test_dispatch_set_brightness(self, service: ClockService, adapter: MagicMock) -> None:
        result = service.dispatch_command(
            device_id="clock-1",
            command_type="set_brightness",
            payload={"deviceId": "clock-1", "type": "set_brightness", "level": 75},
        )
        assert result == {"result": "updated"}

    def test_invalid_device_id_raises(self, service: ClockService, adapter: MagicMock) -> None:
        with pytest.raises(InvalidDeviceId):
            service.dispatch_command(
                device_id="clock/1",  # '/' is invalid
                command_type="set_alarm",
                payload={"deviceId": "clock/1", "type": "set_alarm"},
            )
        adapter.publish.assert_not_called()

    def test_publish_failure_propagates(self, service: ClockService, adapter: MagicMock) -> None:
        adapter.publish.side_effect = DispatchError("Broker unreachable")
        with pytest.raises(DispatchError, match="Broker unreachable"):
            service.dispatch_command(
                device_id="clock-1",
                command_type="display_message",
                payload={
                    "deviceId": "clock-1",
                    "type": "display_message",
                    "message": "Hi",
                    "durationSeconds": 10,
                },
            )

    def test_topic_from_config_prefix(self, config: MqttConfig, adapter: MagicMock) -> None:
        config.topic_prefix = "my/custom/prefix"
        service = ClockService(adapter, config)
        service.dispatch_command(
            device_id="clock-1",
            command_type="set_alarm",
            payload={"deviceId": "clock-1", "type": "set_alarm"},
        )
        adapter.publish.assert_called_once()
        topic = adapter.publish.call_args[0][0]
        assert topic == "my/custom/prefix/clock-1/set_alarm"
