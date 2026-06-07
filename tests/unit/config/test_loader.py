"""Tests for config loader."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import SecretStr

from mqtt_mcp.config.loader import _read_dotenv, load_config
from mqtt_mcp.config.models import AuthMode


class TestLoadConfig:
    """Config loading from env vars and defaults."""

    def test_loads_defaults_when_no_env_overrides(self) -> None:  # noqa: D102
        config = load_config()
        assert config.broker_url == "mqtt://localhost:1883"
        assert config.topic_prefix == "clocks/commands"
        assert config.qos == 1

    def test_overrides_via_dict(self) -> None:  # noqa: D102
        config = load_config(overrides={"broker_url": "mqtt://broker:1883", "qos": 2})
        assert config.broker_url == "mqtt://broker:1883"
        assert config.qos == 2

    def test_env_var_overrides_default(self, monkeypatch: pytest.MonkeyPatch) -> None:  # noqa: D102
        monkeypatch.setenv("MQTT_MCP_BROKER_URL", "mqtt://env-broker:1883")
        config = load_config()
        assert config.broker_url == "mqtt://env-broker:1883"

    def test_env_var_non_empty_wins(self, monkeypatch: pytest.MonkeyPatch) -> None:  # noqa: D102
        monkeypatch.setenv("MQTT_MCP_QOS", "0")
        config = load_config()
        assert config.qos == 0

    def test_overrides_beat_env_vars(self, monkeypatch: pytest.MonkeyPatch) -> None:  # noqa: D102
        monkeypatch.setenv("MQTT_MCP_BROKER_URL", "mqtt://env-broker:1883")
        config = load_config(overrides={"broker_url": "mqtt://override-broker:1883"})
        assert config.broker_url == "mqtt://override-broker:1883"

    def test_default_retained_is_false(self) -> None:  # noqa: D102
        config = load_config()
        assert config.retained is False

    def test_retained_from_env_var(self, monkeypatch: pytest.MonkeyPatch) -> None:  # noqa: D102
        monkeypatch.setenv("MQTT_MCP_RETAINED", "true")
        config = load_config()
        assert config.retained is True

    def test_retained_override_beats_env_var(self, monkeypatch: pytest.MonkeyPatch) -> None:  # noqa: D102
        monkeypatch.setenv("MQTT_MCP_RETAINED", "true")
        config = load_config(overrides={"retained": False})
        assert config.retained is False

    def test_auth_mode_from_env_var(self, monkeypatch: pytest.MonkeyPatch) -> None:  # noqa: D102
        monkeypatch.setenv("MQTT_MCP_AUTH_MODE", "none")
        config = load_config()
        assert config.auth_mode == AuthMode.NONE

    def test_secret_fields_from_env_vars_remain_secret_str(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:  # noqa: D102
        """Secrets loaded from env vars remain wrapped in SecretStr."""
        monkeypatch.setenv("MQTT_MCP_BROKER_PASSWORD", "broker-secret")
        monkeypatch.setenv("MQTT_MCP_AUTH_TOKEN", "auth-secret")
        config = load_config()
        assert isinstance(config.broker_password, SecretStr)
        assert isinstance(config.auth_token, SecretStr)


class TestReadDotenv:
    """Reading .env files."""

    def test_returns_empty_when_no_file(self, tmp_path: Path) -> None:  # noqa: D102
        result = _read_dotenv(tmp_path / ".env")
        assert result == {}

    def test_reads_env_file(self, tmp_path: Path) -> None:  # noqa: D102
        env_file = tmp_path / ".env"
        env_file.write_text("MQTT_MCP_BROKER_URL=mqtt://dotenv-broker:1883\n")
        result = _read_dotenv(env_file)
        assert result == {"broker_url": "mqtt://dotenv-broker:1883"}

    def test_ignores_unrelated_env_vars(self, tmp_path: Path) -> None:  # noqa: D102
        env_file = tmp_path / ".env"
        env_file.write_text("UNRELATED_VAR=hello\nDEBUG=1\n")
        result = _read_dotenv(env_file)
        assert result == {}

    def test_reads_retained_from_dotenv(self, tmp_path: Path) -> None:  # noqa: D102
        env_file = tmp_path / ".env"
        env_file.write_text("MQTT_MCP_RETAINED=true\n")
        result = _read_dotenv(env_file)
        assert result == {"retained": "true"}

    def test_reads_auth_mode_from_dotenv(self, tmp_path: Path) -> None:  # noqa: D102
        env_file = tmp_path / ".env"
        env_file.write_text("MQTT_MCP_AUTH_MODE=none\n")
        result = _read_dotenv(env_file)
        assert result == {"auth_mode": "none"}

    def test_ignores_empty_supported_values(self, tmp_path: Path) -> None:  # noqa: D102
        env_file = tmp_path / ".env"
        env_file.write_text("MQTT_MCP_RETAINED=\nMQTT_MCP_AUTH_MODE=\n")
        result = _read_dotenv(env_file)
        assert result == {}

    def test_load_config_ignores_empty_dotenv_values(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:  # noqa: D102
        """Blank supported values in .env fall back to defaults."""
        monkeypatch.chdir(tmp_path)
        env_file = tmp_path / ".env"
        env_file.write_text("MQTT_MCP_RETAINED=\n")
        config = load_config()
        assert config.retained is False


class TestEnvExampleDoc:
    """The .env.example file documents supported vars without real secrets."""

    def test_env_example_documents_retained(self) -> None:  # noqa: D102
        env_example = Path(__file__).parents[3] / ".env.example"
        content = env_example.read_text()
        assert "MQTT_MCP_RETAINED" in content

    def test_env_example_documents_auth_mode(self) -> None:  # noqa: D102
        env_example = Path(__file__).parents[3] / ".env.example"
        content = env_example.read_text()
        assert "MQTT_MCP_AUTH_MODE" in content

    def test_env_example_has_no_real_broker_url(self) -> None:  # noqa: D102
        env_example = Path(__file__).parents[3] / ".env.example"
        content = env_example.read_text()
        # Default localhost is acceptable; real remote URLs are not
        lines = [ln for ln in content.splitlines() if ln.startswith("MQTT_MCP_BROKER_URL=")]
        for line in lines:
            value = line.split("=", 1)[1]
            assert "localhost" in value or value == ""
