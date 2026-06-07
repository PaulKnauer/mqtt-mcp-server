You are the Blind Hunter reviewer for Story 1.1.

Rules:
- Review the diff only.
- Do not assume any project context beyond what appears in the diff.
- Focus on bugs, regressions, unsafe assumptions, missing tests, and suspicious behavior.
- Output findings as a Markdown list.
- Each finding must include: short title, severity (`high`, `medium`, or `low`), and evidence from the diff.
- If there are no findings, say `No findings.`

Diff:

```diff
diff --git a/.env.example b/.env.example
index bc1a6e8..93e6824 100644
--- a/.env.example
+++ b/.env.example
@@ -9,8 +9,10 @@ MQTT_MCP_BROKER_URL=mqtt://localhost:1883
 # MQTT settings
 MQTT_MCP_TOPIC_PREFIX=clocks/commands
 MQTT_MCP_QOS=1
+MQTT_MCP_RETAINED=false
 
 # Authentication (optional; leave blank to disable auth)
+MQTT_MCP_AUTH_MODE=none
 # Single token with wildcard scope (legacy):
 MQTT_MCP_AUTH_TOKEN=
 # Multi-credential format: id|token|scope1,scope2;id2|token2|*
diff --git a/src/mqtt_mcp/adapters/mqtt_adapter.py b/src/mqtt_mcp/adapters/mqtt_adapter.py
index 9c3bf4a..6b08b35 100644
--- a/src/mqtt_mcp/adapters/mqtt_adapter.py
+++ b/src/mqtt_mcp/adapters/mqtt_adapter.py
@@ -179,7 +179,7 @@ class MqttAdapter:
         else:
             logger.info("MQTT connection closed cleanly")
 
-    def publish(self, topic: str, payload: str, qos: int = 1) -> None:
+    def publish(self, topic: str, payload: str, qos: int = 1, retain: bool = False) -> None:
         """
         Publish a message to a topic.
 
@@ -187,6 +187,7 @@ class MqttAdapter:
             topic: The MQTT topic to publish to.
             payload: The message payload (will be encoded as UTF-8).
             qos: Quality of Service level (0, 1, or 2).
+            retain: Whether the broker should retain this message for the topic.
 
         Raises:
             DispatchError: if publish fails or client is not connected.
@@ -196,7 +197,7 @@ class MqttAdapter:
             raise DispatchError("MQTT client is not connected")
 
         try:
-            info = self._client.publish(topic, payload, qos=qos, retain=False)
+            info = self._client.publish(topic, payload, qos=qos, retain=retain)
 
             if info.rc != MQTTErrorCode.MQTT_ERR_SUCCESS:
                 raise DispatchError(f"Publish to '{topic}' failed with code {info.rc.name}")
diff --git a/src/mqtt_mcp/config/defaults.py b/src/mqtt_mcp/config/defaults.py
index 41ae528..e3b4c84 100644
--- a/src/mqtt_mcp/config/defaults.py
+++ b/src/mqtt_mcp/config/defaults.py
@@ -8,6 +8,7 @@ DEFAULTS: dict[str, object] = {
     "broker_password": None,
     "topic_prefix": "clocks/commands",
     "qos": 1,
+    "retained": False,
     "auth_token": None,
     "auth_credentials": None,
     "auth_mode": "none",
diff --git a/src/mqtt_mcp/config/loader.py b/src/mqtt_mcp/config/loader.py
index e272a40..bd31b79 100644
--- a/src/mqtt_mcp/config/loader.py
+++ b/src/mqtt_mcp/config/loader.py
@@ -23,6 +23,7 @@ _ENV_MAP: dict[str, str] = {
     "MQTT_MCP_BROKER_PASSWORD": "broker_password",
     "MQTT_MCP_TOPIC_PREFIX": "topic_prefix",
     "MQTT_MCP_QOS": "qos",
+    "MQTT_MCP_RETAINED": "retained",
     "MQTT_MCP_AUTH_MODE": "auth_mode",
     "MQTT_MCP_AUTH_TOKEN": "auth_token",
     "MQTT_MCP_AUTH_CREDENTIALS": "auth_credentials",
diff --git a/src/mqtt_mcp/config/models.py b/src/mqtt_mcp/config/models.py
index 4ec62ba..6ed8d8f 100644
--- a/src/mqtt_mcp/config/models.py
+++ b/src/mqtt_mcp/config/models.py
@@ -64,6 +64,10 @@ class MqttConfig(BaseModel):
         le=2,
         description="MQTT QoS level (0, 1, or 2).",
     )
+    retained: bool = Field(
+        default=False,
+        description="Whether published MQTT messages should be retained by the broker.",
+    )
     auth_mode: AuthMode = Field(
         default=AuthMode.NONE,
         description="Authentication mode: none or static.",
diff --git a/src/mqtt_mcp/services/clock_service.py b/src/mqtt_mcp/services/clock_service.py
index 7a5382d..883a8e0 100644
--- a/src/mqtt_mcp/services/clock_service.py
+++ b/src/mqtt_mcp/services/clock_service.py
@@ -37,6 +37,7 @@ class ClockService:
         self._adapter = adapter
         self._topic_prefix = config.topic_prefix
         self._qos = config.qos
+        self._retained = config.retained
 
     def dispatch_command(
         self,
@@ -73,7 +74,7 @@ class ClockService:
             topic,
         )
 
-        self._adapter.publish(topic, json_payload, qos=self._qos)
+        self._adapter.publish(topic, json_payload, qos=self._qos, retain=self._retained)
 
         return self._result_for(command_type)
 
diff --git a/tests/unit/adapters/test_mqtt_adapter.py b/tests/unit/adapters/test_mqtt_adapter.py
index 449e768..15cdac8 100644
--- a/tests/unit/adapters/test_mqtt_adapter.py
+++ b/tests/unit/adapters/test_mqtt_adapter.py
@@ -159,6 +159,25 @@ class TestMqttAdapterPublish:
         with pytest.raises(DispatchError, match="failed with code"):
             adapter.publish("test/topic", "payload")
 
+    def test_publish_with_retain_true(self) -> None:  # noqa: D102
+        from paho.mqtt.enums import MQTTErrorCode
+
+        adapter, mock_client = self._make_connected_adapter()
+
+        info = MagicMock()
+        info.rc = MQTTErrorCode.MQTT_ERR_SUCCESS
+        info.wait_for_publish.return_value = True
+        info.is_published.return_value = True
+        mock_client.publish.return_value = info
+
+        adapter.publish("test/topic", '{\"key\": \"value\"}', qos=1, retain=True)
+        mock_client.publish.assert_called_once_with(
+            "test/topic",
+            '{\"key\": \"value\"}',
+            qos=1,
+            retain=True,
+        )
+
     def test_publish_qos_wait_timeout_raises(self) -> None:  # noqa: D102
         from paho.mqtt.enums import MQTTErrorCode
 
diff --git a/tests/unit/config/test_loader.py b/tests/unit/config/test_loader.py
index be80c51..4673e3e 100644
--- a/tests/unit/config/test_loader.py
+++ b/tests/unit/config/test_loader.py
@@ -7,6 +7,7 @@ from pathlib import Path
 import pytest
 
 from mqtt_mcp.config.loader import _read_dotenv, load_config
+from mqtt_mcp.config.models import AuthMode
 
 
 class TestLoadConfig:
@@ -38,6 +39,25 @@ class TestLoadConfig:
         config = load_config(overrides={"broker_url": "mqtt://override-broker:1883"})
         assert config.broker_url == "mqtt://override-broker:1883"
 
+    def test_default_retained_is_false(self) -> None:  # noqa: D102
+        config = load_config()
+        assert config.retained is False
+
+    def test_retained_from_env_var(self, monkeypatch: pytest.MonkeyPatch) -> None:  # noqa: D102
+        monkeypatch.setenv("MQTT_MCP_RETAINED", "true")
+        config = load_config()
+        assert config.retained is True
+
+    def test_retained_override_beats_env_var(self, monkeypatch: pytest.MonkeyPatch) -> None:  # noqa: D102
+        monkeypatch.setenv("MQTT_MCP_RETAINED", "true")
+        config = load_config(overrides={"retained": False})
+        assert config.retained is False
+
+    def test_auth_mode_from_env_var(self, monkeypatch: pytest.MonkeyPatch) -> None:  # noqa: D102
+        monkeypatch.setenv("MQTT_MCP_AUTH_MODE", "none")
+        config = load_config()
+        assert config.auth_mode == AuthMode.NONE
+
 
 class TestReadDotenv:
     """Reading .env files."""
@@ -57,3 +77,38 @@ class TestReadDotenv:
         env_file.write_text("UNRELATED_VAR=hello\nDEBUG=1\n")
         result = _read_dotenv(env_file)
         assert result == {}
+
+    def test_reads_retained_from_dotenv(self, tmp_path: Path) -> None:  # noqa: D102
+        env_file = tmp_path / ".env"
+        env_file.write_text("MQTT_MCP_RETAINED=true\n")
+        result = _read_dotenv(env_file)
+        assert result == {"retained": "true"}
+
+    def test_reads_auth_mode_from_dotenv(self, tmp_path: Path) -> None:  # noqa: D102
+        env_file = tmp_path / ".env"
+        env_file.write_text("MQTT_MCP_AUTH_MODE=none\n")
+        result = _read_dotenv(env_file)
+        assert result == {"auth_mode": "none"}
+
+
+class TestEnvExampleDoc:
+    """The .env.example file documents supported vars without real secrets."""
+
+    def test_env_example_documents_retained(self) -> None:  # noqa: D102
+        env_example = Path(__file__).parents[3] / ".env.example"
+        content = env_example.read_text()
+        assert "MQTT_MCP_RETAINED" in content
+
+    def test_env_example_documents_auth_mode(self) -> None:  # noqa: D102
+        env_example = Path(__file__).parents[3] / ".env.example"
+        content = env_example.read_text()
+        assert "MQTT_MCP_AUTH_MODE" in content
+
+    def test_env_example_has_no_real_broker_url(self) -> None:  # noqa: D102
+        env_example = Path(__file__).parents[3] / ".env.example"
+        content = env_example.read_text()
+        # Default localhost is acceptable; real remote URLs are not
+        lines = [ln for ln in content.splitlines() if ln.startswith("MQTT_MCP_BROKER_URL=")]
+        for line in lines:
+            value = line.split("=", 1)[1]
+            assert "localhost" in value or value == ""
diff --git a/tests/unit/config/test_models.py b/tests/unit/config/test_models.py
index 30464bd..d5215c5 100644
--- a/tests/unit/config/test_models.py
+++ b/tests/unit/config/test_models.py
@@ -27,6 +27,10 @@ class TestMqttConfigDefaults:
         config = MqttConfig()
         assert config.auth_mode == AuthMode.NONE
 
+    def test_default_retained(self) -> None:  # noqa: D102
+        config = MqttConfig()
+        assert config.retained is False
+
 
 class TestMqttConfigValidation:
     """Config validation rules."""
@@ -61,6 +65,56 @@ class TestMqttConfigValidation:
         assert config.auth_token is not None
 
 
+class TestMqttConfigRetained:
+    """Retained flag parsing and validation."""
+
+    def test_retained_true_parses(self) -> None:  # noqa: D102
+        config = MqttConfig(retained=True)
+        assert config.retained is True
+
+    def test_retained_false_parses(self) -> None:  # noqa: D102
+        config = MqttConfig(retained=False)
+        assert config.retained is False
+
+    def test_invalid_retained_raises_with_field_name(self) -> None:  # noqa: D102
+        with pytest.raises(ValidationError, match="retained"):
+            MqttConfig(retained="not-a-bool")  # type: ignore[arg-type]
+
+
+class TestMqttConfigSecretFields:
+    """Secret-aware fields stay masked."""
+
+    def test_broker_password_is_secret_str(self) -> None:  # noqa: D102
+        config = MqttConfig(broker_password="hunter2")
+        assert isinstance(config.broker_password, SecretStr)
+        assert "hunter2" not in repr(config.broker_password)
+
+    def test_auth_token_is_secret_str(self) -> None:  # noqa: D102
+        config = MqttConfig(auth_token="my-secret-token")
+        assert isinstance(config.auth_token, SecretStr)
+        assert "my-secret-token" not in repr(config.auth_token)
+
+
+class TestMqttConfigFieldErrors:
+    """Validation errors report the specific field name."""
+
+    def test_broker_url_error_names_field(self) -> None:  # noqa: D102
+        with pytest.raises(ValidationError, match="broker_url"):
+            MqttConfig(broker_url="http://bad")
+
+    def test_qos_error_names_field(self) -> None:  # noqa: D102
+        with pytest.raises(ValidationError, match="qos"):
+            MqttConfig(qos=5)
+
+    def test_auth_mode_error_names_field(self) -> None:  # noqa: D102
+        with pytest.raises(ValidationError, match="auth_mode"):
+            MqttConfig(auth_mode="invalid_mode")  # type: ignore[arg-type]
+
+    def test_retained_error_names_field(self) -> None:  # noqa: D102
+        with pytest.raises(ValidationError, match="retained"):
+            MqttConfig(retained="bad-value")  # type: ignore[arg-type]
+
+
 class TestKnownToolNames:
     """KNOWN_TOOL_NAMES contains all expected tools."""
 
diff --git a/tests/unit/services/test_clock_service.py b/tests/unit/services/test_clock_service.py
index a039be6..b30bb0c 100644
--- a/tests/unit/services/test_clock_service.py
+++ b/tests/unit/services/test_clock_service.py
@@ -44,6 +44,7 @@ class TestClockServiceDispatch:
             "clocks/commands/clock-1/set_alarm",
             '{"deviceId": "clock-1", "type": "set_alarm", "alarmTime": "2030-01-01T07:00:00Z"}',
             qos=1,
+            retain=False,
         )
 
     def test_dispatch_display_message(self, service: ClockService, adapter: MagicMock) -> None:  # noqa: D102
@@ -90,6 +91,22 @@ class TestClockServiceDispatch:
                 },
             )
 
+    def test_dispatch_with_retain_true_passes_flag(self, adapter: MagicMock) -> None:  # noqa: D102
+        config = MqttConfig(
+            broker_url="mqtt://localhost:1883",
+            topic_prefix="clocks/commands",
+            qos=1,
+            retained=True,
+        )
+        svc = ClockService(adapter, config)
+        svc.dispatch_command(
+            device_id="clock-1",
+            command_type="set_alarm",
+            payload={"deviceId": "clock-1", "type": "set_alarm"},
+        )
+        _, kwargs = adapter.publish.call_args
+        assert kwargs["retain"] is True
+
     def test_topic_from_config_prefix(self, config: MqttConfig, adapter: MagicMock) -> None:  # noqa: D102
         config.topic_prefix = "my/custom/prefix"
         service = ClockService(adapter, config)
```
