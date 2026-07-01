"""Ed25519 license key generation and validation. Public key safe to ship in OSS."""
import hashlib
import os
import json
import time
import base64
from pathlib import Path
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

def _free_usage_file() -> Path:
    """Read XBRIDGE_DB_PATH at call time (not import time) so tests can isolate it via env."""
    data_dir = Path(os.environ.get("XBRIDGE_DB_PATH", os.path.expanduser("~/.xbridge")))
    return data_dir / "free_usage.json"

def _identity_hash(key_string: str | None) -> str:
    """Hash the license key (or 'anon' when unset) so the usage file never stores raw keys/emails."""
    return hashlib.sha256((key_string or "anon").encode()).hexdigest()[:16]

def _read_free_usage(usage_file: Path) -> dict:
    try:
        return json.loads(usage_file.read_text())
    except Exception:
        return {}

def _write_free_usage(usage_file: Path, data: dict) -> None:
    try:
        usage_file.parent.mkdir(parents=True, exist_ok=True)
        usage_file.write_text(json.dumps(data))
    except OSError:
        pass  # best-effort persistence; a write failure shouldn't crash the tool call

def check_free_limit(key_string: str | None, max_calls: int = 50) -> bool:
    """
    Returns True if under the daily free-tier limit, False otherwise.

    Persisted to disk (per identity, keyed by a hash of the license key/email)
    so the limit holds across process restarts and across the multiple stdio
    server instances a user may run concurrently — an in-memory dict would be
    per-process and reset on every restart.
    """
    today = time.strftime("%Y%m%d")
    identity = _identity_hash(key_string)
    usage_file = _free_usage_file()

    usage = _read_free_usage(usage_file)
    entry = usage.get(identity, {})
    if entry.get("date") != today:
        entry = {"date": today, "count": 0}
    if entry["count"] >= max_calls:
        return False

    entry["count"] += 1
    usage[identity] = entry
    _write_free_usage(usage_file, usage)
    return True
