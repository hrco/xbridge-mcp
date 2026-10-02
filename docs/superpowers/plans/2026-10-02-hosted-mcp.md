# xBridge Cloud (Hosted Remote MCP) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
> **Execution here ("ultracode"):** each task is handed to a cheap CLI model (opencode free models / grok headless) in its own git worktree; Claude reviews the diff and runs the gate before merging into `feat/hosted-mcp`.

**Goal:** Serve the existing 21 Grok tools over Streamable HTTP at `/mcp`, gated by xBridge license keys, with the caller's own xAI key passed per request.

**Architecture:** A new `xbridge_mcp/cloud.py` ASGI app puts an auth layer in front of the SDK's `StreamableHTTPSessionManager` (stateless) and serves the existing `http_server.py` licensing routes beside it. Auth is a pure function in `cloud_auth.py`. `get_api_key()` reads the `X-XAI-Key` header of the current MCP request.

**Tech Stack:** Python 3.11 venv, `mcp>=1.8,<2` (1.30 installed), Starlette, uvicorn, pytest + pytest-asyncio (`asyncio_mode=auto`), `cryptography` Ed25519.

**Spec:** `docs/superpowers/specs/2026-10-02-hosted-mcp-design.md`

## Global Constraints

- Gate: `.claude/gate.sh` (= `.venv/bin/python -m pytest -q -p no:cacheprovider`). It must pass after every task. Baseline: 279 passed, 3 skipped.
- Never hit the real xAI API in tests; never use `requests`; all HTTP stays `httpx` async.
- Never log, persist, or echo the `X-XAI-Key` or `Authorization` header values.
- Error bodies are JSON `{"error": "<message>"}`.
- MCP tool names keep the `grok-*` prefix. Do not modify any tool handler.
- Commit prefixes `feat: fix: test: docs: chore:`; trailer `Co-Authored-By: <model> <noreply@…>`.
- Keep comments sparse (project style).

## Review Focus

1. **Free-tier counting on handshake traffic:** `initialize` / `tools/list` / notifications must not consume the 50/day. Pinned in Task 4 (`test_handshake_does_not_count`).
2. **Header leak:** the xAI key must never appear in a response body, even on errors. Pinned in Task 3 (`test_error_never_echoes_secrets`) and Task 4 (`test_xai_key_not_in_responses`).
3. **Case of the header names:** clients send `x-xai-key` / `X-XAI-Key` / `authorization` in any case. Pinned in Task 3 (`test_header_names_case_insensitive`).
4. **Re-subscription after cancel:** a cancelled-then-repurchased email must get a working key again, not stay revoked. Pinned in Task 2 (`test_resubscribe_clears_revocation`).
5. **JSON-RPC batch / non-JSON body:** a list body or garbage body must not crash the auth layer (500). Pinned in Task 4 (`test_garbage_body_is_not_500`).

---

### Task 1: Per-request xAI key in `get_api_key()`

**Files:**
- Modify: `xbridge_mcp/server.py:130-138` (`get_api_key`)
- Test: `tests/test_request_api_key.py` (create)

**Interfaces:**
- Produces: `server._request_xai_key() -> str | None`; `get_api_key()` keeps its signature `() -> str`, now preferring the request header.

- [ ] **Step 1: Write the failing test** (`tests/test_request_api_key.py`)

```python
from types import SimpleNamespace

import pytest
from mcp.server.lowlevel.server import request_ctx

from xbridge_mcp import server as srv


def _ctx(headers):
    return SimpleNamespace(request=SimpleNamespace(headers=headers))


def test_env_used_outside_request(monkeypatch):
    monkeypatch.setenv("XAI_API_KEY", "xai-env")
    assert srv.get_api_key() == "xai-env"


def test_header_beats_env(monkeypatch):
    monkeypatch.setenv("XAI_API_KEY", "xai-env")
    token = request_ctx.set(_ctx({"x-xai-key": "xai-header"}))
    try:
        assert srv.get_api_key() == "xai-header"
    finally:
        request_ctx.reset(token)


def test_request_without_header_falls_back_to_env(monkeypatch):
    monkeypatch.setenv("XAI_API_KEY", "xai-env")
    token = request_ctx.set(_ctx({}))
    try:
        assert srv.get_api_key() == "xai-env"
    finally:
        request_ctx.reset(token)


def test_stdio_request_has_no_http_request(monkeypatch):
    monkeypatch.setenv("XAI_API_KEY", "xai-env")
    token = request_ctx.set(SimpleNamespace(request=None))
    try:
        assert srv.get_api_key() == "xai-env"
    finally:
        request_ctx.reset(token)


def test_missing_everywhere_raises(monkeypatch):
    monkeypatch.delenv("XAI_API_KEY", raising=False)
    with pytest.raises(ValueError):
        srv.get_api_key()
```

- [ ] **Step 2: Run it, expect FAIL** on `test_header_beats_env`

Run: `.venv/bin/python -m pytest tests/test_request_api_key.py -v`

- [ ] **Step 3: Implement.** Replace `get_api_key` in `xbridge_mcp/server.py` with:

```python
def _request_xai_key() -> str | None:
    """X-XAI-Key header of the current hosted (HTTP) MCP request, if any."""
    try:
        request = server.request_context.request
    except LookupError:
        return None
    headers = getattr(request, "headers", None)
    if headers is None:
        return None
    return headers.get("x-xai-key") or None


def get_api_key() -> str:
    """xAI API key: the hosted request's X-XAI-Key header, else the XAI_API_KEY env var."""
    api_key = _request_xai_key() or os.environ.get("XAI_API_KEY")
    if not api_key:
        raise ValueError(
            "XAI_API_KEY environment variable is not set. "
            "Please set it with your xAI API key from https://x.ai/api"
        )
    return api_key
```

Starlette `Headers.get` is case-insensitive; the plain dict in the test uses lowercase.

- [ ] **Step 4: Run the test file, then the gate:** `.claude/gate.sh` → all pass.
- [ ] **Step 5: Commit** `feat: read xAI key from the hosted request header`

---

### Task 2: Revocation on subscription cancel/expire

**Files:**
- Modify: `xbridge_mcp/http_server.py` (`webhook_ls`, plus a new `revoked_keys`)
- Test: `tests/test_revocation.py` (create)

**Interfaces:**
- Produces: `http_server.revoked_keys() -> set[str]`, the set of key strings whose `issued_keys.json` entry has `"revoked": true`.
- Behaviour: event `subscription_cancelled` or `subscription_expired` → set `keys[email]["revoked"] = True`, respond `{"status": "revoked", "email": email}` (200; unknown email → `{"status": "ignored"}` 200). Event `subscription_created` for an email whose entry is revoked → issue a **new** key, `revoked` False.

- [ ] **Step 1: Write the failing test** (`tests/test_revocation.py`)

```python
import base64
import hashlib
import hmac
import importlib
import json

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
```

- [ ] **Step 2: Run, expect FAIL** (`AttributeError: revoked_keys`)

Run: `.venv/bin/python -m pytest tests/test_revocation.py -v`

- [ ] **Step 3: Implement** in `xbridge_mcp/http_server.py`:

Add after `_write_keys`:

```python
REVOKE_EVENTS = {"subscription_cancelled", "subscription_expired"}


def revoked_keys() -> set[str]:
    return {e["key"] for e in _read_keys().values() if e.get("revoked") and e.get("key")}
```

In `webhook_ls`, replace

```python
    event = payload.get("meta", {}).get("event_name", "")
    if event != "subscription_created":
        return JSONResponse({"status": "ignored", "event": event})

    attrs = payload.get("data", {}).get("attributes", {})
    product_name = attrs.get("product_name", "")
    email = (attrs.get("user_email", "") or "").strip().lower()

    if not email:
        return JSONResponse({"error": "missing email"}, status_code=400)
```

with

```python
    event = payload.get("meta", {}).get("event_name", "")
    attrs = payload.get("data", {}).get("attributes", {})
    email = (attrs.get("user_email", "") or "").strip().lower()

    if event in REVOKE_EVENTS:
        keys = _read_keys()
        if email not in keys:
            return JSONResponse({"status": "ignored", "event": event})
        keys[email]["revoked"] = True
        _write_keys(keys)
        print(f"[webhook] {event} | {email} | revoked")
        return JSONResponse({"status": "revoked", "email": email})

    if event != "subscription_created":
        return JSONResponse({"status": "ignored", "event": event})

    product_name = attrs.get("product_name", "")

    if not email:
        return JSONResponse({"error": "missing email"}, status_code=400)
```

and change the idempotency guard `if not keys.get(email, {}).get("key"):` to

```python
    existing = keys.get(email, {})
    if not existing.get("key") or existing.get("revoked"):
```

(the dict written inside it has no `revoked` field, which clears the flag).

- [ ] **Step 4: Run test file, then `.claude/gate.sh`** (existing `test_key_provisioning.py` must still pass).
- [ ] **Step 5: Commit** `feat: revoke license keys on subscription cancel/expire`

---

### Task 3: `cloud_auth.authorize`

**Files:**
- Create: `xbridge_mcp/cloud_auth.py`
- Test: `tests/test_cloud_auth.py`

**Interfaces:**
- Consumes: `tokenizer.validate_key(key) -> dict`, `tokenizer.check_free_limit(key) -> bool`.
- Produces:

```python
@dataclass(frozen=True)
class AuthResult:
    ok: bool
    status: int          # 200 when ok
    error: str = ""      # human message, never contains header values
    tier: str = ""

def authorize(headers: Mapping[str, str], revoked: set[str], counts_call: bool) -> AuthResult
```

`headers` may be a Starlette `Headers` (case-insensitive) or a plain dict with any key case. Normalise with `{k.lower(): v for k, v in headers.items()}`.

- [ ] **Step 1: Write the failing test** (`tests/test_cloud_auth.py`)

```python
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
```

- [ ] **Step 2: Run, expect FAIL** (`ModuleNotFoundError: xbridge_mcp.cloud_auth`)

Run: `.venv/bin/python -m pytest tests/test_cloud_auth.py -v`

- [ ] **Step 3: Implement** `xbridge_mcp/cloud_auth.py`:

```python
"""Auth decision for the hosted MCP endpoint. Pure: no I/O beyond the free-tier counter."""
from dataclasses import dataclass
from typing import Mapping

from .tokenizer import check_free_limit, validate_key

FREE_DAILY_CALLS = 50


@dataclass(frozen=True)
class AuthResult:
    ok: bool
    status: int
    error: str = ""
    tier: str = ""


def _deny(status: int, error: str) -> AuthResult:
    return AuthResult(ok=False, status=status, error=error)


def authorize(headers: Mapping[str, str], revoked: set[str], counts_call: bool) -> AuthResult:
    h = {k.lower(): v for k, v in headers.items()}
    auth = h.get("authorization", "")
    key = auth[7:].strip() if auth[:7].lower() == "bearer " else ""
    if not key.startswith("xbrdg_v1."):
        return _deny(401, "missing xBridge key: send Authorization: Bearer xbrdg_v1...")

    result = validate_key(key)
    if not result.get("valid"):
        return _deny(401, f"invalid xBridge key ({result.get('reason', 'unknown')})")
    if key in revoked:
        return _deny(403, "subscription ended: renew at https://xbridgemcp.com")

    xai = h.get("x-xai-key", "")
    if not xai.startswith("xai-"):
        return _deny(400, "missing X-XAI-Key header (your xAI API key, starts with xai-)")

    tier = result.get("tier", "free")
    if tier == "free" and counts_call and not check_free_limit(key, FREE_DAILY_CALLS):
        return _deny(429, f"free tier limit reached ({FREE_DAILY_CALLS}/day): upgrade at https://xbridgemcp.com")
    return AuthResult(ok=True, status=200, tier=tier)
```

- [ ] **Step 4: Run test file, then `.claude/gate.sh`**
- [ ] **Step 5: Commit** `feat: add hosted endpoint auth decision`

---

### Task 4: `cloud.py` ASGI app + packaging

**Files:**
- Create: `xbridge_mcp/cloud.py`
- Modify: `pyproject.toml` (add `cloud` extra and `xbridge-cloud` script)
- Test: `tests/test_cloud_app.py`

**Interfaces:**
- Consumes: `server.server` (the `mcp.server.Server`), `http_server.routes`, `http_server.revoked_keys()`, `cloud_auth.authorize`.
- Produces: `cloud.build_app() -> ASGI callable`, `cloud.main()` (uvicorn on `HOST` default `127.0.0.1`, `PORT` default `8787`).

- [ ] **Step 1: Write the failing test** (`tests/test_cloud_app.py`)

```python
import importlib
import json

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from starlette.testclient import TestClient

from xbridge_mcp import tokenizer

XAI = "xai-secret-123"
MCP_HEADERS = {"Accept": "application/json, text/event-stream", "Content-Type": "application/json"}


@pytest.fixture
def env(monkeypatch, tmp_path):
    priv = Ed25519PrivateKey.generate()
    monkeypatch.setattr(tokenizer, "_public_key", priv.public_key())
    monkeypatch.setenv("XBRIDGE_DB_PATH", str(tmp_path))
    from xbridge_mcp import http_server, cloud
    importlib.reload(http_server)
    importlib.reload(cloud)
    with TestClient(cloud.build_app()) as client:
        yield client, (lambda tier: tokenizer.generate_key("u@x.co", tier, 30, priv))


def rpc(method, id_=1, params=None):
    return json.dumps({"jsonrpc": "2.0", "id": id_, "method": method, "params": params or {}})


INIT = {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "t", "version": "1"}}


def post(client, body, key=None, xai=XAI):
    headers = dict(MCP_HEADERS)
    if key:
        headers["Authorization"] = f"Bearer {key}"
    if xai:
        headers["X-XAI-Key"] = xai
    return client.post("/mcp", content=body, headers=headers)


def test_health_route_still_served(env):
    client, _ = env
    assert client.get("/health").status_code == 200


def test_mcp_without_key_401(env):
    client, _ = env
    r = post(client, rpc("initialize", params=INIT))
    assert r.status_code == 401 and "error" in r.json()


def test_initialize_with_pro_key(env):
    client, sign = env
    r = post(client, rpc("initialize", params=INIT), key=sign("pro"))
    assert r.status_code == 200
    assert r.json()["result"]["serverInfo"]["name"] == "xbridge-mcp"


def test_tools_list_has_all_tools(env):
    client, sign = env
    r = post(client, rpc("tools/list"), key=sign("pro"))
    assert r.status_code == 200
    names = {t["name"] for t in r.json()["result"]["tools"]}
    assert "grok-chat" in names and len(names) >= 21


def test_handshake_does_not_count(env):
    client, sign = env
    k = sign("free")
    for i in range(60):
        assert post(client, rpc("tools/list", id_=i), key=k).status_code == 200


def test_free_tier_51st_tool_call_429(env):
    client, sign = env
    k = sign("free")
    call = rpc("tools/call", params={"name": "grok-models", "arguments": {}})
    # grok-models hits xAI; the call may error inside the tool, but auth must pass 50 times.
    for _ in range(50):
        assert post(client, call, key=k).status_code != 429
    assert post(client, call, key=k).status_code == 429


def test_revoked_key_403(env, monkeypatch):
    client, sign = env
    k = sign("pro")
    from xbridge_mcp import cloud
    monkeypatch.setattr(cloud, "revoked_keys", lambda: {k})
    assert post(client, rpc("tools/list"), key=k).status_code == 403


def test_garbage_body_is_not_500(env):
    client, sign = env
    for body in ("not json", "[]", json.dumps([json.loads(rpc("tools/list"))])):
        assert post(client, body, key=sign("pro")).status_code < 500


def test_xai_key_not_in_responses(env):
    client, sign = env
    for r in (post(client, rpc("tools/list")), post(client, rpc("tools/list"), key=sign("pro"), xai="sk-x"),
              post(client, rpc("tools/list"), key=sign("pro"))):
        assert XAI not in r.text and "sk-x" not in r.text
```

`test_free_tier_51st_tool_call_429` must not reach the real xAI API: add at the top of that test
`monkeypatch.setattr("xbridge_mcp.server.handle_grok_models", _fake)` with
`async def _fake(arguments): from mcp.types import CallToolResult, TextContent; return CallToolResult(content=[TextContent(type="text", text="ok")])`
(add `monkeypatch` to the test's parameters).

- [ ] **Step 2: Run, expect FAIL** (`ImportError: cloud`)

Run: `.venv/bin/python -m pytest tests/test_cloud_app.py -v`

- [ ] **Step 3: Implement** `xbridge_mcp/cloud.py`:

```python
"""xBridge Cloud: hosted Streamable HTTP MCP endpoint + licensing routes."""
import contextlib
import json
import os

import uvicorn
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from starlette.applications import Starlette
from starlette.datastructures import Headers
from starlette.responses import JSONResponse

from .cloud_auth import authorize
from .http_server import revoked_keys, routes
from .server import server

MAX_BODY = 1_000_000


def _counts_call(body: bytes) -> bool:
    try:
        msg = json.loads(body)
    except ValueError:
        return False
    msgs = msg if isinstance(msg, list) else [msg]
    return any(isinstance(m, dict) and m.get("method") == "tools/call" for m in msgs)


def build_app():
    manager = StreamableHTTPSessionManager(app=server, stateless=True, json_response=True)

    @contextlib.asynccontextmanager
    async def lifespan(_app):
        async with manager.run():
            yield

    site = Starlette(routes=routes, lifespan=lifespan)

    async def mcp_endpoint(scope, receive, send):
        body = b""
        more = True
        while more:
            message = await receive()
            body += message.get("body", b"")
            more = message.get("more_body", False)
            if len(body) > MAX_BODY:
                await JSONResponse({"error": "request too large"}, status_code=413)(scope, receive, send)
                return

        counts = scope["method"] == "POST" and _counts_call(body)
        result = authorize(Headers(scope=scope), revoked_keys(), counts)
        if not result.ok:
            await JSONResponse({"error": result.error}, status_code=result.status)(scope, receive, send)
            return

        replayed = False

        async def replay():
            nonlocal replayed
            if not replayed:
                replayed = True
                return {"type": "http.request", "body": body, "more_body": False}
            return await receive()

        await manager.handle_request(scope, replay, send)

    async def app(scope, receive, send):
        if scope["type"] == "http" and scope["path"].rstrip("/") == "/mcp":
            await mcp_endpoint(scope, receive, send)
        else:
            await site(scope, receive, send)

    return app


def main():
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8787"))
    uvicorn.run(build_app(), host=host, port=port, log_level="info", proxy_headers=True)


if __name__ == "__main__":
    main()
```

In `pyproject.toml`, add under `[project.optional-dependencies]`:

```toml
cloud = [
    "starlette>=0.37",
    "uvicorn>=0.30",
]
```

and under `[project.scripts]`: `xbridge-cloud = "xbridge_mcp.cloud:main"`.

If `test_tools_list_has_all_tools` fails because stateless mode requires `initialize` first, do **not** weaken the test: check `mcp/server/lowlevel/server.py` for how `stateless=True` marks the session initialized and report back.

- [ ] **Step 4: Run test file, then `.claude/gate.sh`**
- [ ] **Step 5: Commit** `feat: add hosted Streamable HTTP endpoint (xbridge-cloud)`

---

### Task 5: Deploy files + human runbook

**Files:**
- Create: `deploy/xbridge-cloud.service`, `deploy/nginx-mcp.xbridgemcp.com.conf`, `docs/hosted-runbook.md`
- Test: `tests/test_deploy_files.py`

**Interfaces:** consumes `xbridge-cloud` script and port `8787` from Task 4.

- [ ] **Step 1: Write the failing test** (`tests/test_deploy_files.py`)

```python
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_systemd_unit():
    unit = (ROOT / "deploy/xbridge-cloud.service").read_text()
    assert "ExecStart=/opt/xbridge-mcp/venv/bin/xbridge-cloud" in unit
    assert "EnvironmentFile=/opt/xbridge-mcp/cloud.env" in unit
    assert "XAI_API_KEY" not in unit


def test_nginx_streams_and_proxies():
    conf = (ROOT / "deploy/nginx-mcp.xbridgemcp.com.conf").read_text()
    assert "proxy_pass http://127.0.0.1:8787" in conf
    assert "proxy_buffering off" in conf
    assert "server_name mcp.xbridgemcp.com" in conf
    assert "access_log" in conf and "$http_x_xai_key" not in conf and "$http_authorization" not in conf


def test_runbook_lists_human_steps():
    rb = (ROOT / "docs/hosted-runbook.md").read_text()
    for needle in ("DNS", "certbot", "LS_SIGNING_SECRET", "XBRIDGE_SIGNING_KEY",
                   "subscription_cancelled", "claude mcp add --transport http"):
        assert needle in rb
```

- [ ] **Step 2: Run, expect FAIL** (files missing)
- [ ] **Step 3: Create the files**

`deploy/xbridge-cloud.service`:

```ini
[Unit]
Description=xBridge Cloud (hosted MCP)
After=network-online.target

[Service]
User=xbridge
WorkingDirectory=/opt/xbridge-mcp
EnvironmentFile=/opt/xbridge-mcp/cloud.env
Environment=XBRIDGE_DB_PATH=/opt/xbridge-mcp/data
ExecStart=/opt/xbridge-mcp/venv/bin/xbridge-cloud
Restart=on-failure
MemoryMax=400M

[Install]
WantedBy=multi-user.target
```

`deploy/nginx-mcp.xbridgemcp.com.conf`:

```nginx
server {
    listen 80;
    server_name mcp.xbridgemcp.com;
    access_log /var/log/nginx/mcp.access.log;
    client_max_body_size 1m;

    location / {
        proxy_pass http://127.0.0.1:8787;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_buffering off;
        proxy_read_timeout 600s;
    }
}
```

`docs/hosted-runbook.md`, with sections, each holding exact commands:
1. **Prereqs**: a reachable Ubuntu host (Hostinger `76.13.48.186` timed out on 2026-10-02; alternative Oracle `92.5.184.225`), DNS `A mcp.xbridgemcp.com → <host IP>`.
2. **Install**: `sudo useradd -r -s /usr/sbin/nologin xbridge`; `sudo mkdir -p /opt/xbridge-mcp/data && sudo chown -R xbridge /opt/xbridge-mcp`; `sudo -u xbridge python3 -m venv /opt/xbridge-mcp/venv`; `sudo -u xbridge /opt/xbridge-mcp/venv/bin/pip install "xbridge-mcp[cloud] @ git+https://github.com/hrco/xbridge-mcp@release"`.
3. **Secrets** (`/opt/xbridge-mcp/cloud.env`, mode 600, owner xbridge): `LS_SIGNING_SECRET=` (LemonSqueezy webhook secret), `XBRIDGE_SIGNING_KEY=` (base64 Ed25519 private key matching `tokenizer.ED25519_PUBLIC_KEY_B64`). Never commit.
4. **Service**: copy the unit, `sudo systemctl daemon-reload && sudo systemctl enable --now xbridge-cloud`, `curl -s 127.0.0.1:8787/health`.
5. **nginx + TLS**: copy the conf to `/etc/nginx/sites-available/`, symlink into `sites-enabled`, `sudo nginx -t && sudo systemctl reload nginx`, `sudo certbot --nginx -d mcp.xbridgemcp.com`.
6. **LemonSqueezy**: webhook URL `https://mcp.xbridgemcp.com/webhooks/ls`; events `subscription_created`, `subscription_cancelled`, `subscription_expired`; product description says "Hosted xBridge: no install, unlimited calls".
7. **Smoke test** (customer view): `claude mcp add --transport http xbridge https://mcp.xbridgemcp.com/mcp --header "Authorization: Bearer $XBRIDGE_KEY" --header "X-XAI-Key: $XAI_API_KEY"`, then ask Claude to run `grok-models`.

- [ ] **Step 4: Run test file, then `.claude/gate.sh`**
- [ ] **Step 5: Commit** `docs: add hosted deploy files and runbook`

---

### Task 6: Honest pricing on the site + README hosted section

**Files:**
- Modify: `site/index.html` (pricing section, lines ~163-222), `site/guide.html` (pricing block ~150-166), `README.md` (new `## Hosted (no install)` section before `## Installation`)
- Test: `tests/test_pricing_copy.py`

- [ ] **Step 1: Write the failing test** (`tests/test_pricing_copy.py`)

```python
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAGES = ["site/index.html", "site/guide.html"]


def test_no_stale_prices():
    for p in PAGES:
        html = (ROOT / p).read_text()
        for stale in ("€9", "€3.69", "$0"):
            assert stale not in html, f"{stale} in {p}"


def test_hosted_is_what_pro_sells():
    html = (ROOT / "site/index.html").read_text()
    assert "Hosted" in html
    assert "Self-host" in html and "unlimited" in html.lower()
    assert "mcp.xbridgemcp.com/mcp" in html


def test_readme_hosted_snippet():
    md = (ROOT / "README.md").read_text()
    assert "## Hosted (no install)" in md
    assert "claude mcp add --transport http xbridge https://mcp.xbridgemcp.com/mcp" in md
    assert "X-XAI-Key" in md
```

- [ ] **Step 2: Run, expect FAIL**
- [ ] **Step 3: Edit copy.** Three cards in `site/index.html` `#pricing`, keeping the existing classes and LemonSqueezy button markup:
  - **Self-host** €0/forever: "Unlimited calls · all 21 tools · MIT · pip or Docker · your xAI key". Button → `./guide.html`.
  - **Hosted Free** €0: "50 tool calls/day · no install · one URL in Claude Code/Cursor · your xAI key, never stored". Button → `#free-key` form (existing).
  - **Hosted Pro** (featured, FOUNDER50 badge) `<span class="original-price">€4</span>€2/mo`: "Unlimited hosted calls · no install · founder price locked for life (first 50)". Keep both existing LemonSqueezy buttons.
  - Under the cards, a `<pre><code>` with the `claude mcp add --transport http xbridge https://mcp.xbridgemcp.com/mcp --header "Authorization: Bearer xbrdg_v1…" --header "X-XAI-Key: xai-…"` line.
  - Replace "Self-host for free, or pay a small fee for unlimited calls and convenience." with "Self-host free and unlimited, or let us host it: paste one URL, no Python or Docker."
  - `site/guide.html`: make the pricing block match (€0 self-host unlimited, Hosted Free 50/day, Hosted Pro €4, €2 founders); remove `$0`, `€9`, `€3.69`.
  - `README.md`: add a `## Hosted (no install)` section with the `claude mcp add` line and one sentence: "Your xAI key is sent per request in `X-XAI-Key` and never stored. Free key: 50 calls/day. Pro: unlimited, €4/mo at https://xbridgemcp.com."
- [ ] **Step 4: Run test file, then `.claude/gate.sh`**
- [ ] **Step 5: Commit** `docs: price Pro as hosted MCP, self-host stays free and unlimited`
