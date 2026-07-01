"""
Tests for http_server webhook auth (F1) and /keys/* rate limiting (F3).

Uses tmp_path + XBRIDGE_DB_PATH monkeypatching to isolate each test from the real
/opt/xbridge-mcp/data, and reload()s the module so its module-level DATA_DIR/*_FILE
constants pick up the patched env var before the Starlette app is rebuilt.
"""
import hashlib
import hmac
import importlib
import json
import os
import tempfile

# http_server.py creates DATA_DIR at import time (default /opt/xbridge-mcp/data), which
# isn't writable on a dev/CI box — point it at a throw-away dir before the first import.
os.environ.setdefault("XBRIDGE_DB_PATH", tempfile.mkdtemp(prefix="xbridge-test-"))

import pytest
from starlette.testclient import TestClient

from xbridge_mcp import http_server


@pytest.fixture
def hs(tmp_path, monkeypatch):
    """Fresh http_server module instance backed by a throw-away data dir."""
    monkeypatch.setenv("XBRIDGE_DB_PATH", str(tmp_path))
    monkeypatch.delenv("LS_SIGNING_SECRET", raising=False)
    importlib.reload(http_server)
    yield http_server
    monkeypatch.delenv("LS_SIGNING_SECRET", raising=False)
    importlib.reload(http_server)  # restore module state for other tests


def _client(hs):
    return TestClient(hs.app)


def _signed(secret: str, body: bytes) -> str:
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


class TestWebhookFailsClosed:
    def test_rejected_when_secret_not_configured(self, hs):
        client = _client(hs)
        resp = client.post("/webhooks/ls", json={"meta": {"event_name": "subscription_created"}})
        assert resp.status_code == 401

    def test_rejected_with_wrong_signature(self, hs, monkeypatch):
        monkeypatch.setenv("LS_SIGNING_SECRET", "topsecret")
        client = _client(hs)
        resp = client.post(
            "/webhooks/ls",
            json={"meta": {"event_name": "subscription_created"}},
            headers={"X-Signature": "not-the-right-signature"},
        )
        assert resp.status_code == 401

    def test_rejected_with_missing_signature_header(self, hs, monkeypatch):
        monkeypatch.setenv("LS_SIGNING_SECRET", "topsecret")
        client = _client(hs)
        resp = client.post("/webhooks/ls", json={"meta": {"event_name": "subscription_created"}})
        assert resp.status_code == 401

    def test_accepted_with_valid_signature(self, hs, monkeypatch):
        monkeypatch.setenv("LS_SIGNING_SECRET", "topsecret")
        body = json.dumps({"meta": {"event_name": "ping"}}).encode()
        sig = _signed("topsecret", body)
        client = _client(hs)
        resp = client.post(
            "/webhooks/ls",
            content=body,
            headers={"X-Signature": sig, "Content-Type": "application/json"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "ignored"

    def test_forged_subscription_created_does_not_provision_without_secret(self, hs, tmp_path):
        """The core exploit F1 closes: no secret configured -> forged event must not provision."""
        client = _client(hs)
        resp = client.post(
            "/webhooks/ls",
            json={
                "meta": {"event_name": "subscription_created"},
                "data": {"attributes": {"user_email": "attacker@example.com", "product_name": "Founder"}},
            },
        )
        assert resp.status_code == 401
        counter_file = tmp_path / "founder_count.json"
        assert not counter_file.exists()


class TestKeysRateLimit:
    def test_keys_free_rate_limited_after_max_requests(self, hs):
        client = _client(hs)
        statuses = []
        for i in range(hs.RATE_LIMIT_MAX_REQUESTS + 2):
            resp = client.post("/keys/free", json={"email": f"user{i}@example.com"})
            statuses.append(resp.status_code)
        # All requests share one TestClient IP, so the IP bucket should trip.
        assert 429 in statuses
        assert statuses.index(429) < len(statuses)

    def test_keys_free_email_bucket_limits_independent_of_ip_bucket(self, hs, monkeypatch):
        """A single email retried past the per-email limit is blocked even under the IP cap."""
        client = _client(hs)
        for _ in range(hs.RATE_LIMIT_MAX_REQUESTS):
            client.post("/keys/free", json={"email": "dupe@example.com"})
        resp = client.post("/keys/free", json={"email": "dupe@example.com"})
        assert resp.status_code == 429

    def test_keys_resend_rate_limited_after_max_requests(self, hs):
        client = _client(hs)
        statuses = []
        for i in range(hs.RATE_LIMIT_MAX_REQUESTS + 2):
            resp = client.post("/keys/resend", json={"email": f"user{i}@example.com"})
            statuses.append(resp.status_code)
        assert 429 in statuses
