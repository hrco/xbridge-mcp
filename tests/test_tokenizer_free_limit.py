"""
Tests for tokenizer.check_free_limit — persistent, per-identity free-tier throttling.

Uses tmp_path + XBRIDGE_DB_PATH monkeypatching to isolate each test from the real
~/.xbridge/free_usage.json, and reload()s the module so its path-resolution helpers
pick up the patched env var.
"""
import importlib

import pytest

from xbridge_mcp import tokenizer


@pytest.fixture
def tok(tmp_path, monkeypatch):
    """Fresh tokenizer module instance backed by a throw-away data dir."""
    monkeypatch.setenv("XBRIDGE_DB_PATH", str(tmp_path))
    importlib.reload(tokenizer)
    yield tokenizer
    importlib.reload(tokenizer)  # restore module state for other tests


class TestCheckFreeLimit:
    def test_allows_calls_under_the_limit(self, tok):
        for _ in range(5):
            assert tok.check_free_limit("xbrdg_v1.abc.def", max_calls=5) is True

    def test_blocks_calls_over_the_limit(self, tok):
        for _ in range(5):
            tok.check_free_limit("xbrdg_v1.abc.def", max_calls=5)
        assert tok.check_free_limit("xbrdg_v1.abc.def", max_calls=5) is False

    def test_persists_across_process_restart(self, tok, tmp_path):
        """Simulates a restart: reloading the module must not reset the counter."""
        for _ in range(5):
            tok.check_free_limit("xbrdg_v1.abc.def", max_calls=5)

        importlib.reload(tok)  # simulate a fresh process picking up the same data dir

        assert tok.check_free_limit("xbrdg_v1.abc.def", max_calls=5) is False

    def test_different_identities_get_separate_buckets(self, tok):
        for _ in range(5):
            assert tok.check_free_limit("xbrdg_v1.key-one.sig", max_calls=5) is True
        # A different key must not be blocked by key-one's usage.
        assert tok.check_free_limit("xbrdg_v1.key-two.sig", max_calls=5) is True

    def test_anonymous_calls_share_one_bucket(self, tok):
        """No key at all -> shared 'anon' identity, still enforced (not unlimited)."""
        for _ in range(5):
            assert tok.check_free_limit(None, max_calls=5) is True
        assert tok.check_free_limit(None, max_calls=5) is False

    def test_usage_file_written_to_configured_data_dir(self, tok, tmp_path):
        tok.check_free_limit("xbrdg_v1.abc.def", max_calls=5)
        assert (tmp_path / "free_usage.json").exists()
