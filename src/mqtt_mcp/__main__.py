"""CLI entry point for MQTT MCP server.

Usage:
    python -m mqtt_mcp

Runs preflight validation, creates the server (including MQTT connection),
and starts the stdio transport.
"""

from __future__ import annotations

import logging
import sys

from mqtt_mcp.config.validation import run_preflight
from mqtt_mcp.server import create_server


def main() -> None:
    """Main entry point for the MQTT MCP server."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stderr,
    )

    config = run_preflight()

    # create_server connects the MQTT adapter — any failure propagates
    # as DispatchError, causing a clean exit with a useful log message.
    app = create_server(config)
    app.run(transport="stdio")


if __name__ == "__main__":
    main()
