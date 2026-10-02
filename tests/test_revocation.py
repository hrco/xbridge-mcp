import base64
import hashlib
import hmac
import importlib
import json
import os
import tempfile

# http_server.py creates DATA_DIR at import time (default /opt/xbridge-mcp/data), which
# isn't writable on a dev/CI box — point it at a throw-away dir before the first import.
os.environ.setdefault("XBRIDGE_DB_PATH", tempfile.mkdtemp(prefix="xbridge-revoke-"))

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, NoEncryption, PrivateFormat
from starlette.testclient import TestClient

from xbridge_mcp import http_server

SECRET = "topsecret"


@pytest.fixture
def hs(tmp_path, monkeypatch):
    raw = Ed25519PrivateKey.generate().private_bytes(Encoding.Raw, PrivateFormat.Raw, NoEncryption())
    monkeypatch.setenv("XBRIDGE_DB_PATH", str(tmp_path))
    monkeypatch.setenv("LS_SIGNING_SECRET", SECRET)
    monkeypatch.setenv("XBRIDGE_SIGNING_KEY", base64.b64encode(raw).decode())
    importlib.reload(http_server)
    yield http_server
    monkeypatch.delenv("LS_SIGNING_SECRET", raising=False)
    monkeypatch.delenv("XBRIDGE_SIGNING_KEY", raising=False)
    importlib.reload(http_server)


def _event(client, event, email, product="xBridge Pro", order_id="ord-1"):
    body = json.dumps({
        "meta": {"event_name": event},
        "data": {"id": order_id, "attributes": {
            "product_name": product, "variant_name": product,
            "user_email": email, "order_id": order_id,
        }},
    }).encode()
    sig = hmac.new(SECRET.encode(), body, hashlib.sha256).hexdigest()
    return client.post("/webhooks/ls", content=body,
                       headers={"X-Signature": sig, "Content-Type": "application/json"})


def _key_for(hs, email):
    return json.loads(hs.KEYS_FILE.read_text())[email]["key"]


@pytest.mark.parametrize("event", ["subscription_cancelled", "subscription_expired"])
def test_cancel_revokes_key(hs, event):
    c = TestClient(hs.app)
    _event(c, "subscription_created", "a@b.co")
    key = _key_for(hs, "a@b.co")
    assert key not in hs.revoked_keys()
    r = _event(c, event, "a@b.co")
    assert r.status_code == 200 and r.json()["status"] == "revoked"
    assert key in hs.revoked_keys()


def test_cancel_unknown_email_is_ignored(hs):
    r = _event(TestClient(hs.app), "subscription_cancelled", "nobody@b.co")
    assert r.status_code == 200 and r.json()["status"] == "ignored"


def test_resubscribe_clears_revocation(hs):
    c = TestClient(hs.app)
    _event(c, "subscription_created", "a@b.co")
    old = _key_for(hs, "a@b.co")
    _event(c, "subscription_cancelled", "a@b.co")
    _event(c, "subscription_created", "a@b.co", order_id="ord-2")
    new = _key_for(hs, "a@b.co")
    assert new != old
    assert new not in hs.revoked_keys()


def test_cancel_requires_valid_signature(hs):
    c = TestClient(hs.app)
    _event(c, "subscription_created", "a@b.co")
    body = json.dumps({"meta": {"event_name": "subscription_cancelled"},
                       "data": {"attributes": {"user_email": "a@b.co"}}}).encode()
    r = c.post("/webhooks/ls", content=body, headers={"X-Signature": "bad"})
    assert r.status_code == 401
    assert _key_for(hs, "a@b.co") not in hs.revoked_keys()