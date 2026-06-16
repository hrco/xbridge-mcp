"""Ed25519 license key generation and validation. Public key safe to ship in OSS."""
import os
import json
import time
import base64
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives import serialization
from cryptography.exceptions import InvalidSignature

ED25519_PUBLIC_KEY_B64 = "CcEV5dbrnyvGNL8zXg4OIye0ASylmzt33wrtwNq+uGo="

_public_key = None

def _get_public_key() -> Ed25519PublicKey:
    global _public_key
    if _public_key is None:
        raw = base64.b64decode(ED25519_PUBLIC_KEY_B64)
        _public_key = Ed25519PublicKey.from_public_bytes(raw)
    return _public_key

def validate_key(key_string: str | None) -> dict:
    """
    Validate a license key. Returns:
      {"valid": True, "tier": "pro", "email": "..."}  or  {"valid": False, "reason": "..."}
    If no key provided, returns free-tier defaults.
    """
    if not key_string or not key_string.startswith("xbrdg_v1."):
        return {"valid": True, "tier": "free", "email": ""}

    try:
        parts = key_string.split(".")
        if len(parts) != 3:
            return {"valid": False, "reason": "malformed key"}

        payload_b64, sig_b64 = parts[1], parts[2]
        payload_bytes = base64.urlsafe_b64decode(payload_b64 + "==")
        sig_bytes = base64.urlsafe_b64decode(sig_b64 + "==")

        _get_public_key().verify(sig_bytes, payload_bytes)

        payload = json.loads(payload_bytes.decode())

        if payload.get("exp", 0) < int(time.time()):
            return {"valid": False, "reason": "expired"}

        return {
            "valid": True,
            "tier": payload.get("tier", "free"),
            "email": payload.get("email", ""),
        }
    except (InvalidSignature, Exception):
        return {"valid": False, "reason": "invalid signature"}

def generate_key(email: str, tier: str, days: int, private_key: Ed25519PrivateKey) -> str:
    """Generate a signed license key. Called by gen-key.py, never in production code."""
    payload = {
        "email": email,
        "tier": tier,
        "exp": int(time.time()) + days * 86400,
    }
    payload_bytes = json.dumps(payload).encode()
    sig = private_key.sign(payload_bytes)

    payload_b64 = base64.urlsafe_b64encode(payload_bytes).rstrip(b"=").decode()
    sig_b64 = base64.urlsafe_b64encode(sig).rstrip(b"=").decode()

    return f"xbrdg_v1.{payload_b64}.{sig_b64}"

_free_usage: dict[str, list[float]] = {}

def check_free_limit(key_string: str | None, max_calls: int = 50) -> bool:
    """Returns True if under limit. Auto-resets daily."""
    import hashlib
    today = time.strftime("%Y%m%d")
    h = hashlib.sha256((key_string or "anon").encode()).hexdigest()[:12]
    entry = _free_usage.get(h, {})
    if entry.get("date") != today:
        _free_usage[h] = {"date": today, "count": 0}
    if _free_usage[h]["count"] >= max_calls:
        return False
    _free_usage[h]["count"] += 1
    return True
