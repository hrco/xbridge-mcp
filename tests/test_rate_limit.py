"""Tests for _check_rate_limit — BYOK unlimited, invalid-key rejection, free-tier cap."""
import importlib

import pytest

from xbridge_mcp import server as srv_module
from xbridge_mcp.server import _check_rate_limit


@pytest.fixture
def rate_env(tmp_path, monkeypatch):
    """Isolate free-tier usage file and reload modules for clean state."""
    monkeypatch.setenv("XBRIDGE_DB_PATH", str(tmp_path))
    import xbridge_mcp.tokenizer as tok
    importlib.reload(tok)
    importlib.reload(srv_module)
    yield srv_module
    importlib.reload(tok)
    importlib.reload(srv_module)


class TestCheckRateLimit:
    def test_no_key_is_unlimited(self, rate_env):
        assert _check_rate_limit(None) is None
        assert _check_rate_limit("") is None

    def test_invalid_key_returns_error_not_keyerror(self, rate_env):
        result = _check_rate_limit("xbrdg_v1.badpayload.badsig")
        assert result is not None
        assert result.isError is True
        assert "invalid" in result.content[0].text.lower()

    def test_expired_key_returns_error(self, rate_env, monkeypatch):
        monkeypatch.setattr(
            "xbridge_mcp.server.validate_key",
            lambda _k: {"valid": False, "reason": "expired"},
        )
        result = _check_rate_limit("xbrdg_v1.any.any")
        assert result is not None
        assert result.isError is True
        assert "expired" in result.content[0].text.lower()

    def test_valid_pro_key_is_unlimited(self, rate_env, monkeypatch):
        monkeypatch.setattr(
            "xbridge_mcp.server.validate_key",
            lambda _k: {"valid": True, "tier": "pro", "email": "pro@example.com"},
        )
        assert _check_rate_limit("xbrdg_v1.pro.sig") is None

    def test_free_tier_key_enforces_daily_cap(self, rate_env, monkeypatch):
        monkeypatch.setattr(
            "xbridge_mcp.server.validate_key",
            lambda _k: {"valid": True, "tier": "free", "email": "free@example.com"},
        )
        key = "xbrdg_v1.free.sig"
        for _ in range(50):
            assert _check_rate_limit(key) is None
        blocked = _check_rate_limit(key)
        assert blocked is not None
        assert blocked.isError is True
        assert "50 calls/day" in blocked.content[0].text