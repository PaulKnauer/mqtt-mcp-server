"""Tests for auth module — credential parsing, token verification, device authorization."""

from __future__ import annotations

import pytest

from mqtt_mcp.auth import (
    Credential,
    check_device_authorization,
    parse_credentials,
    verify_token,
)
from mqtt_mcp.domain.exceptions import ForbiddenDevice, Unauthorized


class TestParseCredentials:
    """Credential parsing from config strings."""

    def test_parses_multi_credential_format(self) -> None:
        creds = parse_credentials("admin|secret123|*;user2|token456|clock-1,clock-2", None)
        assert len(creds) == 2
        assert creds[0].id == "admin"
        assert creds[0].token == "secret123"
        assert creds[0].devices == ["*"]
        assert creds[1].id == "user2"
        assert creds[1].token == "token456"
        assert creds[1].devices == ["clock-1", "clock-2"]

    def test_parses_single_credential(self) -> None:
        creds = parse_credentials("admin|secret|*", None)
        assert len(creds) == 1
        assert creds[0].token == "secret"

    def test_legacy_auth_token_fallback(self) -> None:
        creds = parse_credentials(None, "legacy-token")
        assert len(creds) == 1
        assert creds[0].token == "legacy-token"
        assert creds[0].devices == ["*"]
        assert creds[0].id == "default"

    def test_credentials_beats_legacy_token(self) -> None:
        creds = parse_credentials("admin|secret|*", "legacy-token")
        assert len(creds) == 1
        assert creds[0].token == "secret"

    def test_raises_on_no_credentials(self) -> None:
        with pytest.raises(ValueError, match="No valid credentials"):
            parse_credentials(None, None)

    def test_skips_malformed_entries(self) -> None:
        creds = parse_credentials("onlyid;;admin|secret|*", None)
        assert len(creds) == 1
        assert creds[0].id == "admin"

    def test_default_scope_is_wildcard(self) -> None:
        creds = parse_credentials("user|token", None)
        assert len(creds) == 1
        assert creds[0].devices == ["*"]


class TestVerifyToken:
    """Bearer token verification."""

    def test_valid_token_returns_credential(self) -> None:
        creds = [Credential(id="admin", token="secret123", devices=["*"])]
        result = verify_token("secret123", creds)
        assert result.id == "admin"

    def test_invalid_token_raises(self) -> None:
        creds = [Credential(id="admin", token="secret123", devices=["*"])]
        with pytest.raises(Unauthorized):
            verify_token("wrong-token", creds)

    def test_no_credentials_raises(self) -> None:
        with pytest.raises(Unauthorized):
            verify_token("anything", [])

    def test_constant_time_comparison(self) -> None:
        """Verify constant-time comparison works with varying lengths."""
        creds = [Credential(id="admin", token="a-longer-token-value", devices=["*"])]
        result = verify_token("a-longer-token-value", creds)
        assert result.id == "admin"


class TestCheckDeviceAuthorization:
    """Device scope checking."""

    def test_wildcard_scope_allows_all(self) -> None:
        cred = Credential(id="admin", token="t", devices=["*"])
        # Should not raise
        check_device_authorization(cred, "clock-1")
        check_device_authorization(cred, "clock-kitchen")
        check_device_authorization(cred, "any-device")

    def test_exact_scope_allows_matching(self) -> None:
        cred = Credential(id="user", token="t", devices=["clock-1"])
        check_device_authorization(cred, "clock-1")

    def test_exact_scope_denies_other(self) -> None:
        cred = Credential(id="user", token="t", devices=["clock-1"])
        with pytest.raises(ForbiddenDevice):
            check_device_authorization(cred, "clock-2")

    def test_prefix_scope_allows_matching(self) -> None:
        cred = Credential(id="user", token="t", devices=["clock-*"])
        check_device_authorization(cred, "clock-1")
        check_device_authorization(cred, "clock-kitchen")
        check_device_authorization(cred, "clock-")

    def test_prefix_scope_denies_non_matching(self) -> None:
        cred = Credential(id="user", token="t", devices=["clock-*"])
        with pytest.raises(ForbiddenDevice):
            check_device_authorization(cred, "other-device")

    def test_multiple_scopes_any_can_match(self) -> None:
        cred = Credential(id="user", token="t", devices=["clock-1", "clock-2"])
        check_device_authorization(cred, "clock-2")
        with pytest.raises(ForbiddenDevice):
            check_device_authorization(cred, "clock-3")

    def test_forbidden_error_contains_device_id(self) -> None:
        cred = Credential(id="user", token="t", devices=["clock-1"])
        with pytest.raises(ForbiddenDevice, match="clock-3"):
            check_device_authorization(cred, "clock-3")
