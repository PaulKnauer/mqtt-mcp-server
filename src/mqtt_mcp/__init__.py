"""MQTT MCP server for smart clock devices."""

from mqtt_mcp.config.validation import run_preflight
from mqtt_mcp.server import create_server

__all__ = ["create_server", "run_preflight"]
