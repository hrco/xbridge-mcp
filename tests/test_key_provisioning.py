"""
Tests for the money path: a paid LemonSqueezy webhook must issue + persist a signed
license key, and the buyer must be able to self-retrieve it via /keys/mine.

Isolated from real state via XBRIDGE_DB_PATH; a throw-away Ed25519 signing key is
injected via XBRIDGE_SIGNING_KEY so _load_signing_key() succeeds.
"""
import base64
import hashlib
import hmac
import importlib
import json
import os
import tempfile

os.environ.setdefault("XBRIDGE_DB_PATH", tempfile.mkdtemp(prefix="xbridge-prov-"))

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, NoEncryption, PrivateFormat
from starlette.testclient import TestClient

from xbridge_mcp import http_server

SECRET = "topsecret"


def _signing_key_b64() -> str:
    raw = Ed25519PrivateKey.generate().private_bytes(Encoding.Raw, PrivateFormat.Raw, NoEncryption())
    return base64.b64encode(raw).decode()


@pytest.fixture
def hs(tmp_path, monkeypatch):
    monkeypatch.setenv("XBRIDGE_DB_PATH", str(tmp_path))
    monkeypatch.setenv("LS_SIGNING_SECRET", SECRET)
    monkeypatch.setenv("XBRIDGE_SIGNING_KEY", _signing_key_b64())
    importlib.reload(http_server)
    yield http_server
    for var in ("LS_SIGNING_SECRET", "XBRIDGE_SIGNING_KEY"):
        monkeypatch.delenv(var, raising=False)
    importlib.reload(http_server)


def _post_subscription(client, product_name, email, order_id="ord-123"):
    body = json.dumps({
        "meta": {"event_name": "subscription_created"},
        "data": {
            "id": order_id,
            "attributes": {
                "product_name": product_name,
                "variant_name": product_name,
                "user_email": email,
                "order_id": order_id,
            },
        },
    }).encode()
    sig = hmac.new(SECRET.encode(), body, hashlib.sha256).hexdigest()
    return client.post("/webhooks/ls", content=body, headers={"X-Signature": sig, "Content-Type": "application/json"})


class TestPaidProvisioning:
    def test_founder_purchase_issues_and_persists_key(self, hs, tmp_path):
        client = TestClient(hs.app)
        resp = _post_subscription(client, "xBridge Founder", "buyer@example.com")
        assert resp.status_code == 200
        assert resp.json()["tier"] == "founder"
        stored = json.loads((tmp_path / "issued_keys.json").read_text())
        assert stored["buyer@example.com"]["key"].startswith("xbrdg_v1.")
        assert stored["buyer@example.com"]["tier"] == "founder"
        assert stored["buyer@example.com"]["order_id"] == "ord-123"

    def test_buyer_can_retrieve_key_via_keys_mine(self, hs):
        client = TestClient(hs.app)
        _post_subscription(client, "xBridge Founder", "buyer@example.com")
        resp = client.post("/keys/mine", json={"email": "buyer@example.com", "order_id": "ord-123"})
        assert resp.status_code == 200
        assert resp.json()["key"].startswith("xbrdg_v1.")
        assert resp.json()["tier"] == "founder"

    def test_pro_purchase_issues_pro_key(self, hs):
        client = TestClient(hs.app)
        resp = _post_subscription(client, "xBridge Pro", "pro@example.com")
        assert resp.status_code == 200
        assert resp.json()["tier"] == "pro"

    def test_email_is_normalized_case_insensitive(self, hs):
        client = TestClient(hs.app)
        _post_subscription(client, "xBridge Founder", "MixedCase@Example.com")
        resp = client.post("/keys/mine", json={"email": "mixedcase@example.com", "order_id": "ord-123"})
        assert resp.status_code == 200

    def test_repeat_webhook_is_idempotent_seat_and_key(self, hs):
        client = TestClient(hs.app)
        _post_subscription(client, "xBridge Founder", "buyer@example.com")
        first = client.post("/keys/mine", json={"email": "buyer@example.com", "order_id": "ord-123"}).json()["key"]
        _post_subscription(client, "xBridge Founder", "buyer@example.com")
        second = client.post("/keys/mine", json={"email": "buyer@example.com", "order_id": "ord-123"}).json()["key"]
        assert first == second  # not regenerated
        assert TestClient(hs.app).get("/founder-status").json()["founder_seats_used"] == 1  # one seat


class TestKeysMineRetrieval:
    def test_unknown_email_returns_404(self, hs):
        client = TestClient(hs.app)
        resp = client.post("/keys/mine", json={"email": "nobody@example.com", "order_id": "whatever"})
        assert resp.status_code == 404

    def test_invalid_email_returns_400(self, hs):
        client = TestClient(hs.app)
        resp = client.post("/keys/mine", json={"email": "not-an-email", "order_id": "ord-123"})
        assert resp.status_code == 400

    def test_wrong_order_id_returns_404(self, hs):
        client = TestClient(hs.app)
        _post_subscription(client, "xBridge Founder", "buyer@example.com")
        resp = client.post("/keys/mine", json={"email": "buyer@example.com", "order_id": "wrong-order"})
        assert resp.status_code == 404

    def test_missing_order_id_returns_400(self, hs):
        client = TestClient(hs.app)
        _post_subscription(client, "xBridge Founder", "buyer@example.com")
        resp = client.post("/keys/mine", json={"email": "buyer@example.com"})
        assert resp.status_code == 400

    def test_blank_order_id_returns_400(self, hs):
        client = TestClient(hs.app)
        _post_subscription(client, "xBridge Founder", "buyer@example.com")
        resp = client.post("/keys/mine", json={"email": "buyer@example.com", "order_id": ""})
        assert resp.status_code == 400
