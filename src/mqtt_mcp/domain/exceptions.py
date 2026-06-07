"""
Domain-specific exception types for MQTT MCP server.

Typed exceptions allow services and tools to distinguish
validation failures from infrastructure errors.
"""

from __future__ import annotations

from enum import StrEnum, auto


class ErrorCategory(StrEnum):
    """Categories for domain and infrastructure errors."""

    VALIDATION = auto()
    AUTH = auto()
    DISPATCH = auto()
    INTERNAL = auto()


class MqttMCPError(Exception):
    """Base exception for all MQTT MCP server errors."""

    def __init__(self, message: str, category: ErrorCategory = ErrorCategory.INTERNAL) -> None:  # noqa: D107
        self.category = category
        super().__init__(message)


class DomainError(MqttMCPError):
    """Base for domain validation errors."""

    def __init__(  # noqa: D107
        self,
        message: str,
        field: str | None = None,
        suggestion: str | None = None,
    ) -> None:
        self.field = field
        self.suggestion = suggestion
        super().__init__(message, ErrorCategory.VALIDATION)


class BrightnessOutOfRangeError(DomainError):
    """Raised when brightness level is outside 0-100."""

    def __init__(self, level: int) -> None:  # noqa: D107
        super().__init__(
            message=f"Brightness must be 0-100, got {level}",
            field="level",
            suggestion="Brightness must be between 0 (off) and 100 (max).",
        )


class EmptyMessageError(DomainError):
    """Raised when message is empty or whitespace only."""

    def __init__(self) -> None:  # noqa: D107
        super().__init__(
            message="Message must not be empty",
            field="message",
            suggestion="Provide a non-empty message string.",
        )


class DurationOutOfRangeError(DomainError):
    """Raised when duration is outside 1-3600."""

    def __init__(self, duration: int) -> None:  # noqa: D107
        super().__init__(
            message=f"Duration must be 1-3600 seconds, got {duration}",
            field="durationSeconds",
            suggestion="Duration must be between 1 and 3600 seconds (1 hour).",
        )


class PastAlarmTimeError(DomainError):
    """Raised when alarm time is in the past."""

    def __init__(self, alarm_time: str) -> None:  # noqa: D107
        super().__init__(
            message=f"Alarm time must be in the future, got {alarm_time}",
            field="alarmTime",
            suggestion="Provide an alarm time that is in the future (RFC3339 format).",
        )


class InvalidDeviceIdError(DomainError):
    """Raised when device ID format is invalid."""

    def __init__(self, device_id: str) -> None:  # noqa: D107
        super().__init__(
            message=f"Invalid device ID: {device_id}",
            field="deviceId",
            suggestion="Device ID must be 1-64 alphanumeric characters, hyphens, or underscores.",
        )


class UnauthorizedError(MqttMCPError):
    """Raised when authentication fails."""

    def __init__(self, message: str = "unauthorized") -> None:  # noqa: D107
        super().__init__(message, ErrorCategory.AUTH)


class ForbiddenDeviceError(MqttMCPError):
    """Raised when the credential scope does not cover the target device."""

    def __init__(self, device_id: str) -> None:  # noqa: D107
        super().__init__(
            message=f"forbidden for target device: {device_id}",
            category=ErrorCategory.AUTH,
        )


class DispatchError(MqttMCPError):
    """Raised when MQTT publish fails."""

    def __init__(self, message: str) -> None:  # noqa: D107
        super().__init__(message, ErrorCategory.DISPATCH)
