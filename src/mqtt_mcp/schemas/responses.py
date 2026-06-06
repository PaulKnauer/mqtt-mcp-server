"""Pydantic response and error schemas for MQTT MCP server."""

from __future__ import annotations

from pydantic import BaseModel


class CommandResponse(BaseModel):
    """Standard success response for command tools."""

    result: str


class ErrorResponse(BaseModel):
    """Structured error response with category, field, and suggestion."""

    error: str
    category: str = "internal"
    field: str | None = None
    suggestion: str | None = None


class ServerInfoResponse(BaseModel):
    """Response for the server_info tool."""

    version: str = "0.1.0"
    mqtt_connected: bool = False
    topic_prefix: str = "clocks/commands"
    auth_enabled: bool = False
