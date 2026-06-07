"""
Clock service — business logic for dispatching commands to smart clocks.

Validates commands through domain safety rules and publishes them
via the MQTT adapter.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from mqtt_mcp.adapters.mqtt_adapter import MqttAdapter
from mqtt_mcp.config.models import MqttConfig
from mqtt_mcp.domain.safety import validate_device_id

logger = logging.getLogger("mqtt_mcp")


class ClockService:
    """
    Service for dispatching commands to smart clock devices.

    Validates commands and publishes them via MQTT.
    """

    def __init__(self, adapter: MqttAdapter, config: MqttConfig) -> None:
        """
        Initialize the clock service.

        Args:
            adapter: MQTT adapter for publishing commands.
            config: Server configuration (topic prefix, QoS, etc.).

        """
        self._adapter = adapter
        self._topic_prefix = config.topic_prefix
        self._qos = config.qos

    def dispatch_command(
        self,
        device_id: str,
        command_type: str,
        payload: dict[str, Any],
    ) -> dict[str, str]:
        """
        Validate and dispatch a command to a smart clock device.

        Args:
            device_id: Target device identifier.
            command_type: Command type string (e.g. "set_alarm").
            payload: Command-specific payload to publish.

        Returns:
            A result dict with a single "result" key.

        Raises:
            DomainError: if validation fails.
            DispatchError: if MQTT publish fails.
            ForbiddenDeviceError: if the auth principal is not authorized.

        """
        validate_device_id(device_id)

        topic = f"{self._topic_prefix}/{device_id}/{command_type}"
        json_payload = json.dumps(payload, ensure_ascii=False, default=str)

        logger.info(
            "Dispatching %s to %s via topic %s",
            command_type,
            device_id,
            topic,
        )

        self._adapter.publish(topic, json_payload, qos=self._qos)

        return self._result_for(command_type)

    @staticmethod
    def _result_for(command_type: str) -> dict[str, str]:
        """
        Return the success result dict for a command type.

        Matches clock-server's response contract:
        - set_alarm → {"result": "scheduled"}
        - display_message → {"result": "sent"}
        - set_brightness → {"result": "updated"}
        """
        results: dict[str, str] = {
            "set_alarm": "scheduled",
            "display_message": "sent",
            "set_brightness": "updated",
        }
        return {"result": results.get(command_type, "dispatched")}
