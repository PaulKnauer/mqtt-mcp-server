"""Tests for config loader."""

from __future__ import annotations

from pathlib import Path

import pytest

from mqtt_mcp.config.loader import _read_dotenv, load_config


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
