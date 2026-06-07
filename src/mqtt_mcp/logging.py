"""
JSON log formatter for structured logging.

Produces single-line JSON records parseable by log aggregators
(CloudWatch, Datadog, Loki, etc.) without external dependencies.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime


class JsonFormatter(logging.Formatter):
    """Format log records as JSON objects, one per line."""

    def format(self, record: logging.LogRecord) -> str:
        """
        Format a log record as a JSON line.

        Args:
            record: The log record to format.

        Returns:
            A JSON string with timestamp, level, logger, message, and
            any extra fields set via ``logger.info("msg", extra={...})``.

        """
        payload: dict[str, object] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Include exception info if present
        if record.exc_info and record.exc_info[1]:
            payload["exception"] = {
                "type": type(record.exc_info[1]).__name__,
                "message": str(record.exc_info[1]),
            }

        # Include any extra fields set by the caller
        for key, value in record.__dict__.items():
            if key not in (
                "args",
                "asctime",
                "created",
                "exc_info",
                "exc_text",
                "filename",
                "funcName",
                "levelname",
                "levelno",
                "lineno",
                "message",
                "module",
                "msecs",
                "msg",
                "name",
                "pathname",
                "process",
                "processName",
                "relativeCreated",
                "stack_info",
                "thread",
                "threadName",
            ):
                payload[key] = value

        return json.dumps(payload, default=str, ensure_ascii=False)
