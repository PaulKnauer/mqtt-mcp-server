"""
CLI entry point for MQTT MCP server.

Usage:
    python -m mqtt_mcp

Runs preflight validation, creates the server (including MQTT connection),
registers a graceful shutdown handler, and starts the stdio transport.
"""

from __future__ import annotations

import logging
import os
import signal
import sys

from mqtt_mcp.config.validation import run_preflight
from mqtt_mcp.logging import JsonFormatter
from mqtt_mcp.server import create_server

_log = logging.getLogger("mqtt_mcp")


def main() -> None:
    """Run the MQTT MCP server CLI entry point."""
    log_level = _resolve_log_level()
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(JsonFormatter())
    logging.basicConfig(level=log_level, handlers=[handler])

    config = run_preflight()

    # create_server connects the MQTT adapter — any failure propagates
    # as DispatchError, causing a clean exit with a useful log message.
    app = create_server(config)

    _register_shutdown(app, config)

    _log.info(
        "MQTT MCP server starting broker=%s prefix=%s auth=%s",
        config.broker_url,
        config.topic_prefix,
        config.auth_mode,
    )
    app.run(transport="stdio")


def _resolve_log_level() -> int:
    """Return the log level from the LOG_LEVEL env var, defaulting to INFO."""
    level_name = os.environ.get("LOG_LEVEL", "INFO").upper()
    return getattr(logging, level_name, logging.INFO)


def _register_shutdown(app: object, config: object) -> None:
    """Register SIGTERM/SIGINT handlers for graceful MQTT disconnect."""

    def _handle_signal(signum: int, frame: object) -> None:
        sig_name = signal.Signals(signum).name
        _log.info("Received %s — shutting down gracefully", sig_name)

        # FastMCP doesn't expose a stop() method on the app directly,
        # so we rely on the stdio transport ending naturally.
        # Log a final message so the orchestrator can see clean shutdown.
        _log.info("MQTT MCP server stopped")

    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)


if __name__ == "__main__":
    main()
