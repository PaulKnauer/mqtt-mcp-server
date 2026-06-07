"""
Tool permissions — maps tool names to allowed/known sets.

The single source of truth for known tool names is
``config.models.KNOWN_TOOL_NAMES``. Keeping the set in config lets
startup validation and tool registration share one contract.
"""

from __future__ import annotations

from mqtt_mcp.config.models import KNOWN_TOOL_NAMES


def is_tool_permitted(tool_name: str) -> bool:
    """
    Return True if the named tool is known to the server.

    Args:
        tool_name: The MCP tool name to check.

    """
    return tool_name in KNOWN_TOOL_NAMES


def assert_tool_permitted(tool_name: str) -> None:
    """
    Raise ValueError if the tool name is unknown.

    Args:
        tool_name: The MCP tool name to check.

    Raises:
        ValueError: if the tool name is not in KNOWN_TOOL_NAMES.

    """
    if not is_tool_permitted(tool_name):
        allowed_tools = ", ".join(sorted(KNOWN_TOOL_NAMES))
        raise ValueError(f"Unknown tool: {tool_name}. Allowed values: {allowed_tools}.")
