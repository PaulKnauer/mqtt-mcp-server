"""Tests for the setup support tools (ping, server_info)."""

from __future__ import annotations

from unittest.mock import MagicMock

from pydantic import SecretStr

from mqtt_mcp.adapters.mqtt_adapter import MqttAdapter
from mqtt_mcp.config.models import AuthMode, MqttConfig
from mqtt_mcp.tools.setup_support import register_setup_support


def _get_tool_fn(app, name):
    """Get a registered tool's callable function."""
    tool = app._tool_manager.get_tool(name)
    assert tool is not None, f"Tool '{name}' not found"
    return tool.fn


class TestPing:
    """ping tool returns status ok."""

    def test_ping_returns_ok(self) -> None:  # noqa: D102
        from mcp.server.fastmcp import FastMCP

        app = FastMCP("test")
        config = MqttConfig(broker_url="mqtt://localhost:1883")
        adapter = MagicMock(spec=MqttAdapter)
        register_setup_support(app, config, adapter)
        result = _get_tool_fn(app, "ping")()
        assert result == {"status": "ok"}


class TestServerInfo:
    """server_info returns server metadata."""

    def test_returns_default_fields(self) -> None:  # noqa: D102
        from mcp.server.fastmcp import FastMCP

        app = FastMCP("test")
        config = MqttConfig(broker_url="mqtt://localhost:1883")
        adapter = MagicMock(spec=MqttAdapter)
        adapter.is_ready.return_value = False
        register_setup_support(app, config, adapter)
        result = _get_tool_fn(app, "server_info")()
        assert result["version"] == "0.1.0"
        assert result["mqtt_connected"] is False
        assert result["topic_prefix"] == "clocks/commands"
        assert result["auth_enabled"] is False

    def test_reports_mqtt_connected(self) -> None:  # noqa: D102
        from mcp.server.fastmcp import FastMCP

        app = FastMCP("test")
        config = MqttConfig(broker_url="mqtt://localhost:1883")
        adapter = MagicMock(spec=MqttAdapter)
        adapter.is_ready.return_value = True
        register_setup_support(app, config, adapter)
        result = _get_tool_fn(app, "server_info")()
        assert result["mqtt_connected"] is True

    def test_auth_enabled_when_static(self) -> None:  # noqa: D102
        from mcp.server.fastmcp import FastMCP

        app = FastMCP("test")
        config = MqttConfig(
            broker_url="mqtt://localhost:1883",
            auth_mode=AuthMode.STATIC,
            auth_token=SecretStr("secret"),
        )
        adapter = MagicMock(spec=MqttAdapter)
        register_setup_support(app, config, adapter)
        result = _get_tool_fn(app, "server_info")()
        assert result["auth_enabled"] is True

    def test_custom_topic_prefix(self) -> None:  # noqa: D102
        from mcp.server.fastmcp import FastMCP

        app = FastMCP("test")
        config = MqttConfig(
            broker_url="mqtt://localhost:1883",
            topic_prefix="my/custom/prefix",
        )
        adapter = MagicMock(spec=MqttAdapter)
        register_setup_support(app, config, adapter)
        result = _get_tool_fn(app, "server_info")()
        assert result["topic_prefix"] == "my/custom/prefix"
