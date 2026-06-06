"""Typed configuration models for MQTT MCP server.

Uses Pydantic for validation, matching sonos-mcp-server's config pattern.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field, SecretStr, field_validator

KNOWN_TOOL_NAMES: frozenset[str] = frozenset(
    {
        "ping",
        "server_info",
        "set_alarm",
        "display_message",
        "set_brightness",
    }
)


class AuthMode(StrEnum):
    """Supported authentication modes."""

    NONE = "none"
    STATIC = "static"


class LogLevel(StrEnum):
    """Standard Python log levels."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


class MqttConfig(BaseModel):
    """Validated runtime configuration for MQTT MCP server."""

    broker_url: str = Field(
        default="mqtt://localhost:1883",
        description="MQTT broker URL (mqtt:// or mqtts://).",
    )
    broker_username: str | None = Field(
        default=None,
        description="MQTT broker username.",
    )
    broker_password: SecretStr | None = Field(
        default=None,
        description="MQTT broker password.",
    )
    topic_prefix: str = Field(
        default="clocks/commands",
        description="MQTT topic prefix for clock commands.",
        min_length=1,
    )
    qos: int = Field(
        default=1,
        ge=0,
        le=2,
        description="MQTT QoS level (0, 1, or 2).",
    )
    auth_mode: AuthMode = Field(
        default=AuthMode.NONE,
        description="Authentication mode: none or static.",
    )
    auth_token: SecretStr | None = Field(
        default=None,
        description="Legacy single bearer token (wildcard device scope).",
    )
    auth_credentials: str | None = Field(
        default=None,
        description="Multi-credential format: id|token|scope1,scope2;id2|token2|*",
    )
    log_level: LogLevel = Field(
        default=LogLevel.INFO,
        description="Application log level.",
    )

    model_config = {"str_strip_whitespace": True, "extra": "forbid"}

    @field_validator("broker_url")
    @classmethod
    def validate_broker_url(cls, value: str) -> str:
        """Validate that broker URL starts with mqtt:// or mqtts://."""
        if not value or not (value.startswith("mqtt://") or value.startswith("mqtts://")):
            raise ValueError(f"broker_url must start with mqtt:// or mqtts://, got '{value}'")
        return value

    @field_validator("topic_prefix")
    @classmethod
    def validate_topic_prefix(cls, value: str) -> str:
        """Validate topic prefix is non-empty and doesn't end with /."""
        stripped = value.strip("/")
        if not stripped:
            raise ValueError("topic_prefix must not be empty")
        return stripped
