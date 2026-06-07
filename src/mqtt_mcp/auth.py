"""
Authentication module for MQTT MCP server.

Provides Bearer token verification with device-scoped credentials,
matching clock-server's auth model adapted for MCP tool context.
"""

from __future__ import annotations

import hmac
import logging
from typing import NamedTuple

from mqtt_mcp.domain.exceptions import DomainError, ForbiddenDeviceError, UnauthorizedError
from mqtt_mcp.domain.safety import validate_device_id

logger = logging.getLogger("mqtt_mcp")


class Credential(NamedTuple):
    """A parsed credential with token and device scope."""

    id: str
    token: str
    devices: list[str]


def parse_credentials(auth_credentials: str | None, auth_token: str | None) -> list[Credential]:
    """
    Parse credential strings into a list of Credential objects.

    Supports two formats:
      1. Multi-credential: ``id|token|scope1,scope2;id2|token2|*``
      2. Legacy single token: ``auth_token`` (wildcard scope ``*``)

    Args:
        auth_credentials: Multi-credential string, or None.
        auth_token: Legacy single token fallback, or None.

    Returns:
        A list of parsed credentials.

    Raises:
        ValueError: if no credentials could be parsed.

    """
    credentials: list[Credential] = []

    if auth_credentials:
        for entry in auth_credentials.split(";"):
            entry = entry.strip()
            if not entry:
                continue
            parts = [p.strip() for p in entry.split("|")]
            if len(parts) < 2:
                logger.warning("Skipping malformed credential entry: %s", entry)
                continue
            cred_id = parts[0]
            token = parts[1]
            if not cred_id:
                raise ValueError("Credential id must not be empty")
            if not token:
                raise ValueError(f"Credential token must not be empty for id '{cred_id}'")
            scopes = [s.strip() for s in parts[2].split(",")] if len(parts) > 2 else ["*"]
            if any(scope == "" for scope in scopes):
                raise ValueError(f"Credential scopes must not be empty for id '{cred_id}'")
            _validate_scopes(cred_id, scopes)
            credentials.append(Credential(id=cred_id, token=token, devices=scopes))

    if not credentials and auth_token:
        credentials.append(Credential(id="default", token=auth_token, devices=["*"]))

    if not credentials:
        raise ValueError("No valid credentials configured")

    return credentials


def _validate_scopes(cred_id: str, scopes: list[str]) -> None:
    """Validate credential device scopes."""
    for scope in scopes:
        if scope == "*":
            continue
        if scope.endswith("*"):
            prefix = scope[:-1]
            if not prefix:
                raise ValueError(f"Invalid device scope '{scope}' for id '{cred_id}'")
            _validate_scope_device_id(cred_id, scope, prefix.rstrip("-_") or prefix)
            continue
        _validate_scope_device_id(cred_id, scope, scope)


def _validate_scope_device_id(cred_id: str, scope: str, device_id: str) -> None:
    """Validate one scope component and raise config-oriented errors."""
    try:
        validate_device_id(device_id)
    except DomainError as exc:
        raise ValueError(f"Invalid device scope '{scope}' for id '{cred_id}': {exc}") from exc


def verify_token(token: str, credentials: list[Credential]) -> Credential:
    """
    Verify a bearer token against configured credentials.

    Uses constant-time comparison to prevent timing attacks.

    Args:
        token: The bearer token to verify.
        credentials: List of valid credentials.

    Returns:
        The matching Credential.

    Raises:
        UnauthorizedError: if no credential matches the token.

    """
    for cred in credentials:
        if hmac.compare_digest(token, cred.token):
            return cred
    raise UnauthorizedError()


def check_device_authorization(credential: Credential, device_id: str) -> None:
    """
    Check if a credential is authorized for a specific device.

    Scope matching:
    - ``*``: allows all devices
    - ``clock-*``: prefix match (any ID starting with ``clock-``)
    - ``clock-1``: exact match

    Args:
        credential: The authenticated credential.
        device_id: The target device ID.

    Raises:
        ForbiddenDeviceError: if the credential's scope does not cover the device.

    """
    for scope in credential.devices:
        if scope == "*":
            return
        if scope.endswith("*"):
            prefix = scope[:-1]
            if device_id.startswith(prefix):
                return
        if scope == device_id:
            return

    raise ForbiddenDeviceError(device_id)
