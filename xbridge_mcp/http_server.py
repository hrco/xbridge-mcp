"""xBridge HTTP server — health, webhooks, key delivery."""
import os
import sys
import json
import time
import base64
import hashlib
import hmac
from pathlib import Path
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, PlainTextResponse
from starlette.routing import Route
import uvicorn

sys.path.insert(0, str(Path(__file__).parent.parent))
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

def _make_signed_key(email: str, tier: str, days: int, private_key: Ed25519PrivateKey) -> str:
    """Generate a signed license key."""
    payload = {"email": email, "tier": tier, "exp": int(time.time()) + days * 86400}
    payload_bytes = json.dumps(payload).encode()
    sig = private_key.sign(payload_bytes)
    p = base64.urlsafe_b64encode(payload_bytes).rstrip(b"=").decode()
    s = base64.urlsafe_b64encode(sig).rstrip(b"=").decode()
    return f"xbrdg_v1.{p}.{s}"

DATA_DIR = Path(os.environ.get("XBRIDGE_DB_PATH", "/opt/xbridge-mcp/data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)
FOUNDER_CAP = 50
COUNTER_FILE = DATA_DIR / "founder_count.json"
KEYS_FILE = DATA_DIR / "issued_keys.json"
RATE_LIMIT_FILE = DATA_DIR / "rate_limits.json"
RATE_LIMIT_WINDOW_SECONDS = 3600
RATE_LIMIT_MAX_REQUESTS = 5

def _load_signing_key():
    raw = os.environ.get("XBRIDGE_SIGNING_KEY", "")
    if raw:
        return Ed25519PrivateKey.from_private_bytes(base64.b64decode(raw))
    keyfile = Path("/opt/xbridge-mcp/data/signing_key")
    if keyfile.exists():
        return Ed25519PrivateKey.from_private_bytes(keyfile.read_bytes())
    raise RuntimeError("No signing key configured. Set XBRIDGE_SIGNING_KEY env var.")

def _read_keys():
    try:
        return json.loads(KEYS_FILE.read_text())
    except Exception:
        return {}

def _write_keys(data):
    KEYS_FILE.write_text(json.dumps(data))

def _read_counter():
    try:
        return json.loads(COUNTER_FILE.read_text())
    except Exception:
        return {"count": 0, "emails": []}

def _write_counter(data):
    COUNTER_FILE.write_text(json.dumps(data))

def _read_rate_limits():
    try:
        return json.loads(RATE_LIMIT_FILE.read_text())
    except Exception:
        return {}

def _write_rate_limits(data):
    RATE_LIMIT_FILE.write_text(json.dumps(data))

def _check_and_record_rate_limit(bucket: str, identifier: str) -> bool:
    """Returns True if under the rate limit, recording this request. Fixed window per bucket:identifier."""
    now = time.time()
    key = f"{bucket}:{identifier}"
    limits = _read_rate_limits()
    hits = [t for t in limits.get(key, []) if now - t < RATE_LIMIT_WINDOW_SECONDS]
    if len(hits) >= RATE_LIMIT_MAX_REQUESTS:
        return False
    hits.append(now)
    limits[key] = hits
    _write_rate_limits(limits)
    return True

def _verify_webhook(request: Request) -> bool:
    """Fail CLOSED: reject if the signing secret isn't configured or the signature doesn't match."""
    secret = os.environ.get("LS_SIGNING_SECRET", "")
    if not secret:
        return False
    sig = request.headers.get("X-Signature", "")
    raw = request.state.body
    if not sig or not raw:
        return False
    expected = hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()
    return hmac.compare_digest(sig, expected)

async def health(request):
    return PlainTextResponse("OK")

async def version_info(request):
    return JSONResponse({"name": "xbridge-mcp", "version": "3.0.0", "status": "operational"})

async def founder_status(request):
    data = _read_counter()
    return JSONResponse({"founder_seats_used": data["count"], "founder_cap": FOUNDER_CAP, "remaining": FOUNDER_CAP - data["count"]})

async def webhook_ls(request: Request):
    raw = await request.body()
    request.state.body = raw

    if not _verify_webhook(request):
        return JSONResponse({"error": "invalid or missing webhook signature"}, status_code=401)

    payload = {}
    try:
        payload = json.loads(raw)
    except Exception:
        return JSONResponse({"error": "invalid json"}, status_code=400)

    event = payload.get("meta", {}).get("event_name", "")
    if event != "subscription_created":
        return JSONResponse({"status": "ignored", "event": event})

    attrs = payload.get("data", {}).get("attributes", {})
    product_name = attrs.get("product_name", "")
    email = attrs.get("user_email", "")

    if not email:
        return JSONResponse({"error": "missing email"}, status_code=400)

    if "founder" in product_name.lower() or "founder" in attrs.get("variant_name", "").lower():
        data = _read_counter()
        if data["count"] >= FOUNDER_CAP:
            return JSONResponse({"error": "Founder tier sold out (50/50)"}, status_code=410)
        if email in data["emails"]:
            return JSONResponse({"status": "ok", "note": "already claimed founder"}, status_code=200)
        data["count"] += 1
        data["emails"].append(email)
        _write_counter(data)
        tier = "founder"
    else:
        tier = "pro"

    print(f"[webhook] {event} | {email} | tier={tier} | founder_count={_read_counter()['count']}/{FOUNDER_CAP}")

    return JSONResponse({"status": "ok", "tier": tier, "email": email})

async def keys_free(request: Request):
    client_ip = request.client.host if request.client else "unknown"
    if not _check_and_record_rate_limit("keys_free_ip", client_ip):
        return JSONResponse({"error": "Too many requests. Try again later."}, status_code=429)

    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "invalid json"}, status_code=400)

    email = (body.get("email") or "").strip().lower()
    if not email or "@" not in email:
        return JSONResponse({"error": "valid email required"}, status_code=400)

    if not _check_and_record_rate_limit("keys_free_email", email):
        return JSONResponse({"error": "Too many requests. Try again later."}, status_code=429)

    keys = _read_keys()
    if email in keys:
        return JSONResponse({"error": "This email already has a key. Use the resend link."}, status_code=409)

    try:
        pk = _load_signing_key()
        key = _make_signed_key(email, "free", 36500, pk)
    except RuntimeError as e:
        return JSONResponse({"error": str(e)}, status_code=500)

    keys[email] = {"tier": "free", "created": int(time.time())}
    _write_keys(keys)

    print(f"[keys] free key issued to {email}")
    return JSONResponse({"key": key, "tier": "free", "email": email})

async def keys_resend(request: Request):
    client_ip = request.client.host if request.client else "unknown"
    if not _check_and_record_rate_limit("keys_resend_ip", client_ip):
        return JSONResponse({"error": "Too many requests. Try again later."}, status_code=429)

    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "invalid json"}, status_code=400)

    email = (body.get("email") or "").strip().lower()
    if not email:
        return JSONResponse({"error": "email required"}, status_code=400)

    if not _check_and_record_rate_limit("keys_resend_email", email):
        return JSONResponse({"error": "Too many requests. Try again later."}, status_code=429)

    keys = _read_keys()
    if email not in keys:
        return JSONResponse({"error": "No key found for this email."}, status_code=404)

    return JSONResponse({"status": "ok", "message": "Check your inbox. If using self-host, your original key is still valid."})

routes = [
    Route("/health", health),
    Route("/", version_info),
    Route("/founder-status", founder_status),
    Route("/webhooks/ls", webhook_ls, methods=["POST"]),
    Route("/keys/free", keys_free, methods=["POST"]),
    Route("/keys/resend", keys_resend, methods=["POST"]),
]

app = Starlette(routes=routes)

def main():
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8000"))
    print(f"[xbridge-http] starting on {host}:{port}")
    uvicorn.run(app, host=host, port=port, log_level="info")

if __name__ == "__main__":
    main()
