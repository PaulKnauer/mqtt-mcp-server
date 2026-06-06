"""MQTT adapter wrapping paho-mqtt for clock command publishing.

Provides connect, publish, and disconnect with connection retry
and typed error handling.
"""

from __future__ import annotations

import logging
import time
from urllib.parse import urlparse

import paho.mqtt.client as mqtt
from paho.mqtt.enums import CallbackAPIVersion, MQTTErrorCode
from pydantic import SecretStr

from mqtt_mcp.domain.exceptions import DispatchError

logger = logging.getLogger("mqtt_mcp")

_MAX_RETRIES = 3
_RETRY_DELAY_S = 1.0


class MqttAdapter:
    """paho-mqtt wrapper for publishing clock commands.

    Provides a simple interface for connecting to a broker,
    publishing messages, and clean disconnection.
    """

    def __init__(self) -> None:
        self._client: mqtt.Client | None = None
        self._connected = False

    def connect(
        self,
        broker_url: str,
        username: str | None = None,
        password: str | None = None,
    ) -> None:
        """Connect to the MQTT broker with retry.

        Args:
            broker_url: MQTT broker URL (mqtt://host:port or mqtts://host:port).
            username: Optional broker username.
            password: Optional broker password.

        Raises:
            DispatchError: if connection fails after all retries.
        """
        parsed = urlparse(broker_url)
        host = parsed.hostname or "localhost"
        port = parsed.port or (8883 if parsed.scheme == "mqtts" else 1883)

        client = mqtt.Client(
            callback_api_version=CallbackAPIVersion.VERSION2,
            client_id="",
            clean_session=True,
        )

        if username:
            pw = password.get_secret_value() if isinstance(password, SecretStr) else password
            client.username_pw_set(username, pw)

        # For mqtts://, enable TLS
        if parsed.scheme == "mqtts":
            client.tls_set()

        last_error: Exception | None = None
        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                result = client.connect(host, port, keepalive=60)
                if result != MQTTErrorCode.MQTT_ERR_SUCCESS:
                    raise DispatchError(f"Connection failed with code {result.name}")
                client.loop_start()
                self._client = client
                self._connected = True
                logger.info(
                    "Connected to MQTT broker %s:%d (attempt %d/%d)",
                    host,
                    port,
                    attempt,
                    _MAX_RETRIES,
                )
                return
            except (OSError, DispatchError) as exc:
                last_error = exc
                logger.warning(
                    "MQTT connection attempt %d/%d failed: %s",
                    attempt,
                    _MAX_RETRIES,
                    exc,
                )
                if attempt < _MAX_RETRIES:
                    time.sleep(_RETRY_DELAY_S * attempt)

        self._connected = False
        raise DispatchError(
            f"Failed to connect to MQTT broker at {broker_url} "
            f"after {_MAX_RETRIES} attempts: {last_error}"
        )

    def publish(self, topic: str, payload: str, qos: int = 1) -> None:
        """Publish a message to a topic.

        Args:
            topic: The MQTT topic to publish to.
            payload: The message payload (will be encoded as UTF-8).
            qos: Quality of Service level (0, 1, or 2).

        Raises:
            DispatchError: if publish fails or client is not connected.
        """
        if not self._connected or self._client is None:
            raise DispatchError("MQTT client is not connected")

        info = self._client.publish(topic, payload, qos=qos, retain=False)

        if info.rc != MQTTErrorCode.MQTT_ERR_SUCCESS:
            raise DispatchError(f"Publish to '{topic}' failed with code {info.rc.name}")

        logger.debug("Published to %s (qos=%d): %s", topic, qos, payload)

    def disconnect(self) -> None:
        """Disconnect from the MQTT broker."""
        if self._client is not None:
            self._client.loop_stop()
            self._client.disconnect()
            self._client = None
        self._connected = False
        logger.info("Disconnected from MQTT broker")

    def close(self) -> None:
        """Alias for disconnect, for use in context managers."""
        self.disconnect()

    def is_ready(self) -> bool:
        """Return True if connected to the broker."""
        return self._connected
