"""Tests for the MQTT adapter."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from mqtt_mcp.adapters.mqtt_adapter import MqttAdapter
from mqtt_mcp.domain.exceptions import DispatchError


class TestMqttAdapterConnect:
    """Connecting to the MQTT broker."""

    @staticmethod
    def _make_mock_client() -> MagicMock:
        """Create a mock paho-mqtt Client with successful connect."""
        from paho.mqtt.enums import MQTTErrorCode

        mock_client = MagicMock()
        mock_client.connect.return_value = MQTTErrorCode.MQTT_ERR_SUCCESS
        return mock_client

    def test_successful_connect_parses_url(self) -> None:  # noqa: D102
        adapter = MqttAdapter()
        with patch("mqtt_mcp.adapters.mqtt_adapter.mqtt.Client") as mock_client_cls:
            mock_client_cls.return_value = self._make_mock_client()

            adapter.connect("mqtt://broker:1883")
            mock_client_cls.return_value.connect.assert_called_once_with(
                "broker",
                1883,
                keepalive=60,
            )
            assert adapter.is_ready()

    def test_successful_connect_default_port(self) -> None:  # noqa: D102
        adapter = MqttAdapter()
        with patch("mqtt_mcp.adapters.mqtt_adapter.mqtt.Client") as mock_client_cls:
            mock_client_cls.return_value = self._make_mock_client()

            adapter.connect("mqtt://localhost")
            mock_client_cls.return_value.connect.assert_called_once_with(
                "localhost",
                1883,
                keepalive=60,
            )
            assert adapter.is_ready()

    def test_connect_with_username_password(self) -> None:  # noqa: D102
        adapter = MqttAdapter()
        with patch("mqtt_mcp.adapters.mqtt_adapter.mqtt.Client") as mock_client_cls:
            mock_client = self._make_mock_client()
            mock_client_cls.return_value = mock_client

            adapter.connect("mqtt://broker:1883", username="user", password="pass")
            mock_client.username_pw_set.assert_called_once_with("user", "pass")
            assert adapter.is_ready()

    def test_connect_retries_on_failure(self) -> None:  # noqa: D102
        adapter = MqttAdapter()
        with patch("mqtt_mcp.adapters.mqtt_adapter.mqtt.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client_cls.return_value = mock_client
            mock_client.connect.side_effect = OSError("Connection refused")

            with pytest.raises(DispatchError, match="Failed to connect"):
                adapter.connect("mqtt://broker:1883")
            assert mock_client.connect.call_count == 3
            assert not adapter.is_ready()

    def test_connect_mqtts_enables_tls(self) -> None:  # noqa: D102
        adapter = MqttAdapter()
        with patch("mqtt_mcp.adapters.mqtt_adapter.mqtt.Client") as mock_client_cls:
            mock_client = self._make_mock_client()
            mock_client_cls.return_value = mock_client

            adapter.connect("mqtts://broker:8883")
            mock_client.tls_set.assert_called_once()
            mock_client.connect.assert_called_once_with("broker", 8883, keepalive=60)


class TestMqttAdapterPublish:
    """Publishing messages."""

    @staticmethod
    def _make_connected_adapter() -> tuple[MqttAdapter, MagicMock]:
        """Create a connected adapter and its mock client."""
        from paho.mqtt.enums import MQTTErrorCode

        adapter = MqttAdapter()
        with patch("mqtt_mcp.adapters.mqtt_adapter.mqtt.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.connect.return_value = MQTTErrorCode.MQTT_ERR_SUCCESS
            mock_client_cls.return_value = mock_client
            adapter.connect("mqtt://broker:1883")
            return adapter, mock_client

    def test_publish_success(self) -> None:  # noqa: D102
        from paho.mqtt.enums import MQTTErrorCode

        adapter, mock_client = self._make_connected_adapter()

        info = MagicMock()
        info.rc = MQTTErrorCode.MQTT_ERR_SUCCESS
        mock_client.publish.return_value = info

        adapter.publish("test/topic", '{"key": "value"}', qos=1)
        mock_client.publish.assert_called_once_with(
            "test/topic",
            '{"key": "value"}',
            qos=1,
            retain=False,
        )

    def test_publish_when_not_connected(self) -> None:  # noqa: D102
        adapter = MqttAdapter()
        with pytest.raises(DispatchError, match="not connected"):
            adapter.publish("test/topic", "payload")

    def test_publish_failure_raises_dispatch_error(self) -> None:  # noqa: D102
        from paho.mqtt.enums import MQTTErrorCode

        adapter, mock_client = self._make_connected_adapter()

        info = MagicMock()
        info.rc = MQTTErrorCode.MQTT_ERR_NO_CONN
        mock_client.publish.return_value = info

        with pytest.raises(DispatchError, match="failed with code"):
            adapter.publish("test/topic", "payload")


class TestMqttAdapterDisconnect:
    """Disconnecting from the broker."""

    @staticmethod
    def _make_connected_adapter() -> tuple[MqttAdapter, MagicMock]:
        """Create a connected adapter and its mock client."""
        from paho.mqtt.enums import MQTTErrorCode

        adapter = MqttAdapter()
        with patch("mqtt_mcp.adapters.mqtt_adapter.mqtt.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.connect.return_value = MQTTErrorCode.MQTT_ERR_SUCCESS
            mock_client_cls.return_value = mock_client
            adapter.connect("mqtt://broker:1883")
            return adapter, mock_client

    def test_disconnect_cleans_up(self) -> None:  # noqa: D102
        adapter, mock_client = self._make_connected_adapter()
        assert adapter.is_ready()

        adapter.disconnect()
        mock_client.loop_stop.assert_called_once()
        mock_client.disconnect.assert_called_once()
        assert not adapter.is_ready()

    def test_disconnect_when_not_connected(self) -> None:  # noqa: D102
        adapter = MqttAdapter()
        adapter.disconnect()  # Should not raise
        assert not adapter.is_ready()

    def test_close_alias(self) -> None:  # noqa: D102
        adapter = MqttAdapter()
        with patch.object(adapter, "disconnect") as mock_disconnect:
            adapter.close()
            mock_disconnect.assert_called_once()
