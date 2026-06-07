"""Tool permissions — maps tool names to allowed/known sets.

This module replaces the previous placement of ``is_tool_permitted``
and ``assert_tool_permitted`` in ``domain/safety.py``, which created
a hexagonal-architecture violation (domain importing from config).

The single source of truth for known tool names is now this module.
``config/models.KNOWN_TOOL_NAMES`` has been removed; the set lives here.
"""

from __future__ import annotations

KNOWN_TOOL_NAMES: frozenset[str] = frozenset(
    {
        "ping",
        "server_info",
        "set_alarm",
        "display_message",
        "set_brightness",
    }
)


def is_tool_permitted(tool_name: str) -> bool:
    """Return True if the named tool is known to the server.

    Args:
        tool_name: The MCP tool name to check.
    """
    return tool_name in KNOWN_TOOL_NAMES


def assert_tool_permitted(tool_name: str) -> None:
    """Raise ValueError if the tool name is unknown.

    Args:
        tool_name: The MCP tool name to check.

    Raises:
        ValueError: if the tool name is not in KNOWN_TOOL_NAMES.
    """
    if not is_tool_permitted(tool_name):
        allowed_tools = ", ".join(sorted(KNOWN_TOOL_NAMES))
        raise ValueError(f"Unknown tool: {tool_name}. Allowed values: {allowed_tools}.")
