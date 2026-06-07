"""MCP setup and health tools — ping and server_info."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from mqtt_mcp.adapters.mqtt_adapter import MqttAdapter
from mqtt_mcp.config.models import AuthMode, MqttConfig
from mqtt_mcp.tools.permissions import assert_tool_permitted


def register_setup_support(
    app: FastMCP,
    config: MqttConfig,
    adapter: MqttAdapter,
) -> None:
    """Register ping and server_info tools.

    Args:
        app: The FastMCP application.
        config: The server configuration.
        adapter: The MQTT adapter (used to report real connection state).
    """

    @app.tool(name="ping")
    def ping() -> dict[str, str]:
        """Simple liveness check. Returns immediately with no side effects."""
        assert_tool_permitted("ping")
        return {"status": "ok"}

    @app.tool(name="server_info")
    def server_info() -> dict[str, object]:
        """Return server metadata including MQTT broker status and config.

        Returns:
            Dict with version, mqtt_connected, topic_prefix, and auth_enabled.
        """
        assert_tool_permitted("server_info")
        return {
            "version": "0.1.0",
            "mqtt_connected": adapter.is_ready(),
            "topic_prefix": config.topic_prefix,
            "auth_enabled": config.auth_mode != AuthMode.NONE,
        }
