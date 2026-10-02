import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from xbridge_mcp import tokenizer
from xbridge_mcp.cloud_auth import authorize

XAI = "xai-secret-123"


@pytest.fixture
def sign(monkeypatch, tmp_path):
    priv = Ed25519PrivateKey.generate()
    monkeypatch.setattr(tokenizer, "_public_key", priv.public_key())
    monkeypatch.setenv("XBRIDGE_DB_PATH", str(tmp_path))
    return lambda tier, days=30: tokenizer.generate_key("u@x.co", tier, days, priv)


def h(key=None, xai=XAI):
    d = {}
    if key is not None:
        d["Authorization"] = f"Bearer {key}"
    if xai is not None:
        d["X-XAI-Key"] = xai
    return d


def test_missing_bearer_401(sign):
    r = authorize(h(None), set(), True)
    assert (r.ok, r.status) == (False, 401)


def test_non_xbrdg_bearer_401(sign):
    r = authorize(h("sk-whatever"), set(), True)
    assert r.status == 401


def test_bad_signature_401(sign):
    other = Ed25519PrivateKey.generate()
    r = authorize(h(tokenizer.generate_key("u@x.co", "pro", 30, other)), set(), True)
    assert r.status == 401


def test_expired_401(sign):
    r = authorize(h(sign("pro", days=-1)), set(), True)
    assert r.status == 401 and "expired" in r.error


def test_revoked_403(sign):
    k = sign("pro")
    assert authorize(h(k), {k}, True).status == 403


@pytest.mark.parametrize("xai", [None, "", "sk-not-xai"])
def test_missing_or_bad_xai_key_400(sign, xai):
    assert authorize(h(sign("pro"), xai=xai), set(), True).status == 400


def test_pro_ok(sign):
    r = authorize(h(sign("pro")), set(), True)
    assert (r.ok, r.status, r.tier) == (True, 200, "pro")


def test_founder_unlimited(sign):
    k = sign("founder")
    for _ in range(60):
        assert authorize(h(k), set(), True).ok


def test_free_tier_51st_call_429(sign):
    k = sign("free")
    for _ in range(50):
        assert authorize(h(k), set(), True).ok
    r = authorize(h(k), set(), True)
    assert r.status == 429


def test_free_tier_non_call_traffic_not_counted(sign):
    k = sign("free")
    for _ in range(80):
        assert authorize(h(k), set(), False).ok
    assert authorize(h(k), set(), True).ok


def test_header_names_case_insensitive(sign):
    k = sign("pro")
    r = authorize({"authorization": f"Bearer {k}", "x-xai-key": XAI}, set(), True)
    assert r.ok


def test_error_never_echoes_secrets(sign):
    k = sign("pro", days=-1)
    for r in (authorize(h(k), set(), True), authorize(h(sign("pro"), xai="sk-bad"), set(), True)):
        assert XAI not in r.error and k not in r.error and "sk-bad" not in r.error
