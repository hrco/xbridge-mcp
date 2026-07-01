# xBridge MCP v3 — VPS Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate xBridge MCP from AWS (Lambda + DynamoDB + SES) to VPS (FastAPI + SQLite + Resend) with Streamable HTTP MCP transport, so the server runs remotely and works with any MCP-compatible client via a URL.

**Architecture:** A FastMCP-based Streamable HTTP server at `mcp.xbridgemcp.com/mcp` replaces the local stdio process. Per-request `XAI_API_KEY` is injected from HTTP headers via Python `contextvars` — zero cross-user key leakage. SQLite (WAL mode) replaces DynamoDB. Resend HTTP API replaces SES. stdio mode is preserved for local/Docker users. AWS is decommissioned after the new stack is live and LemonSqueezy webhook is switched.

**Tech Stack:** Python 3.12, FastMCP 1.25 (`streamable_http_app`, `stateless_http=True`), FastAPI (Starlette wrapper), aiosqlite, httpx, Resend API, contextvars, uvicorn, nginx, systemd, Let's Encrypt.

---

## File Map

| File | Action | Responsibility |
|------|--------|---------------|
| `xbridge_mcp/tools.py` | **CREATE** | All 19 tool handler functions extracted from server.py |
| `xbridge_mcp/auth.py` | **CREATE** | `contextvars.ContextVar` for per-request XAI_API_KEY + XBRIDGE_KEY |
| `xbridge_mcp/db.py` | **CREATE** | SQLite async CRUD (replaces `aws/src/shared/db.py`) |
| `xbridge_mcp/email_sender.py` | **CREATE** | Resend HTTP email (replaces `aws/src/shared/email.py`) |
| `xbridge_mcp/http_server.py` | **CREATE** | FastMCP HTTP entry point + middleware |
| `xbridge_mcp/migrations/001_initial.sql` | **CREATE** | SQLite schema |
| `xbridge_mcp/server.py` | **MODIFY** | Remove handler logic (moved to tools.py), keep stdio entry point |
| `xbridge_mcp/key_validator.py` | **MODIFY** | Inline SQLite validation (no HTTP round-trip) |
| `xbridge_mcp/session_manager.py` | **MODIFY** | Namespace sessions by key hash (multi-user safety) |
| `deploy/xbridge.service` | **CREATE** | systemd unit for uvicorn |
| `deploy/nginx-mcp.conf` | **CREATE** | nginx proxy config for mcp.xbridgemcp.com |
| `pyproject.toml` | **MODIFY** | Bump to 3.0.0, add aiosqlite dep |
| `tests/test_db.py` | **CREATE** | SQLite layer tests |
| `tests/test_auth.py` | **CREATE** | contextvars isolation tests |
| `tests/test_http_server.py` | **CREATE** | HTTP transport smoke tests |

---

## Task 1: SQLite schema + db module

**Files:**
- Create: `xbridge_mcp/migrations/001_initial.sql`
- Create: `xbridge_mcp/db.py`
- Create: `tests/test_db.py`

### Step 1.1 — Add aiosqlite dependency

- [ ] Edit `pyproject.toml`:

```toml
dependencies = [
    "mcp>=1.0.0",
    "httpx>=0.27.0",
    "aiosqlite>=0.20.0",
]
```

- [ ] Install: `pip install aiosqlite`

### Step 1.2 — Write migration SQL

- [ ] Create `xbridge_mcp/migrations/001_initial.sql`:

```sql
CREATE TABLE IF NOT EXISTS keys (
    key             TEXT PRIMARY KEY,
    email           TEXT NOT NULL,
    tier            TEXT NOT NULL DEFAULT 'free',
    calls_today     INTEGER NOT NULL DEFAULT 0,
    call_date       TEXT NOT NULL DEFAULT '',
    subscription_id TEXT NOT NULL DEFAULT '',
    created_at      TEXT NOT NULL,
    expires_at      TEXT
);

CREATE INDEX IF NOT EXISTS idx_email ON keys(email);
CREATE INDEX IF NOT EXISTS idx_subscription ON keys(subscription_id) WHERE subscription_id != '';
```

### Step 1.3 — Write failing tests

- [ ] Create `tests/test_db.py`:

```python
import pytest
import pytest_asyncio
import aiosqlite
import os
from xbridge_mcp.db import init_db, create_key, get_key, try_increment_free, \
    email_exists, get_key_by_email, get_key_by_sub_id, extend_paid_key, downgrade_key

TEST_DB = "/tmp/test_xbridge.db"


@pytest_asyncio.fixture(autouse=True)
async def fresh_db():
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)
    await init_db(TEST_DB)
    yield
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)


@pytest.mark.asyncio
async def test_create_and_get_key():
    key = await create_key("test@example.com", "free", db_path=TEST_DB)
    assert len(key) == 36  # UUID
    item = await get_key(key, db_path=TEST_DB)
    assert item["email"] == "test@example.com"
    assert item["tier"] == "free"


@pytest.mark.asyncio
async def test_email_exists():
    assert not await email_exists("new@example.com", db_path=TEST_DB)
    await create_key("new@example.com", "free", db_path=TEST_DB)
    assert await email_exists("new@example.com", db_path=TEST_DB)


@pytest.mark.asyncio
async def test_try_increment_free_counts():
    key = await create_key("rate@example.com", "free", db_path=TEST_DB)
    result = await try_increment_free(key, db_path=TEST_DB)
    assert result["valid"] is True
    assert result["tier"] == "free"
    assert result["calls_remaining"] == 49


@pytest.mark.asyncio
async def test_try_increment_free_limit():
    key = await create_key("limit@example.com", "free", db_path=TEST_DB)
    # Exhaust limit
    async with aiosqlite.connect(TEST_DB) as db:
        from datetime import datetime, timezone
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        await db.execute("UPDATE keys SET calls_today=50, call_date=? WHERE key=?", (today, key))
        await db.commit()
    result = await try_increment_free(key, db_path=TEST_DB)
    assert result["calls_remaining"] == 0


@pytest.mark.asyncio
async def test_get_key_by_email():
    await create_key("lookup@example.com", "paid", subscription_id="sub_123", db_path=TEST_DB)
    item = await get_key_by_email("lookup@example.com", db_path=TEST_DB)
    assert item is not None
    assert item["tier"] == "paid"


@pytest.mark.asyncio
async def test_get_key_by_sub_id():
    await create_key("sub@example.com", "paid", subscription_id="sub_456", db_path=TEST_DB)
    item = await get_key_by_sub_id("sub_456", db_path=TEST_DB)
    assert item is not None
    assert item["email"] == "sub@example.com"


@pytest.mark.asyncio
async def test_extend_and_downgrade():
    await create_key("billing@example.com", "paid", subscription_id="sub_789", db_path=TEST_DB)
    await extend_paid_key("sub_789", days=30, db_path=TEST_DB)
    item = await get_key_by_sub_id("sub_789", db_path=TEST_DB)
    assert item["tier"] == "paid"
    await downgrade_key("sub_789", db_path=TEST_DB)
    item = await get_key_by_sub_id("sub_789", db_path=TEST_DB)
    assert item["tier"] == "free"
```

- [ ] Run: `pytest tests/test_db.py -v`
- [ ] Expected: FAIL with `ModuleNotFoundError: xbridge_mcp.db`

### Step 1.4 — Implement db.py

- [ ] Create `xbridge_mcp/db.py`:

```python
import os
import uuid
import aiosqlite
from datetime import datetime, timezone, timedelta
from pathlib import Path

_DEFAULT_DB = os.environ.get("XBRIDGE_DB_PATH", str(Path.home() / ".xbridge" / "keys.db"))
_MIGRATION = Path(__file__).parent / "migrations" / "001_initial.sql"
_FREE_DAILY_LIMIT = 50


async def init_db(db_path: str = _DEFAULT_DB) -> None:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(db_path) as db:
        await db.execute("PRAGMA journal_mode=WAL")
        await db.execute("PRAGMA foreign_keys=ON")
        await db.executescript(_MIGRATION.read_text())
        await db.commit()


async def get_key(key: str, db_path: str = _DEFAULT_DB) -> dict | None:
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM keys WHERE key=?", (key,)) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None


async def create_key(email: str, tier: str, subscription_id: str = "",
                     db_path: str = _DEFAULT_DB) -> str:
    new_key = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    expires_at = None
    if tier == "paid":
        expires_at = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            "INSERT INTO keys(key, email, tier, subscription_id, created_at, expires_at) "
            "VALUES (?,?,?,?,?,?)",
            (new_key, email, tier, subscription_id, now, expires_at),
        )
        await db.commit()
    return new_key


async def email_exists(email: str, db_path: str = _DEFAULT_DB) -> bool:
    async with aiosqlite.connect(db_path) as db:
        async with db.execute("SELECT 1 FROM keys WHERE email=? LIMIT 1", (email,)) as cur:
            return await cur.fetchone() is not None


async def get_key_by_email(email: str, db_path: str = _DEFAULT_DB) -> dict | None:
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM keys WHERE email=? LIMIT 1", (email,)) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None


async def get_key_by_sub_id(subscription_id: str, db_path: str = _DEFAULT_DB) -> dict | None:
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM keys WHERE subscription_id=? LIMIT 1", (subscription_id,)
        ) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None


async def extend_paid_key(subscription_id: str, days: int = 30,
                          db_path: str = _DEFAULT_DB) -> None:
    expires_at = (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            "UPDATE keys SET tier='paid', expires_at=? WHERE subscription_id=?",
            (expires_at, subscription_id),
        )
        await db.commit()


async def downgrade_key(subscription_id: str, db_path: str = _DEFAULT_DB) -> None:
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            "UPDATE keys SET tier='free', expires_at=NULL WHERE subscription_id=?",
            (subscription_id,),
        )
        await db.commit()


async def try_increment_free(key: str, db_path: str = _DEFAULT_DB) -> dict:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    item = await get_key(key, db_path)
    if not item:
        return {"valid": False}

    # Reset counter if new day
    if item["call_date"] != today:
        async with aiosqlite.connect(db_path) as db:
            await db.execute(
                "UPDATE keys SET calls_today=1, call_date=? WHERE key=?", (today, key)
            )
            await db.commit()
        return {"valid": True, "tier": "free", "calls_remaining": _FREE_DAILY_LIMIT - 1}

    if item["calls_today"] >= _FREE_DAILY_LIMIT:
        return {"valid": True, "tier": "free", "calls_remaining": 0}

    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            "UPDATE keys SET calls_today=calls_today+1 WHERE key=? AND call_date=? "
            "AND calls_today<?",
            (key, today, _FREE_DAILY_LIMIT),
        )
        await db.commit()

    item = await get_key(key, db_path)
    remaining = max(0, _FREE_DAILY_LIMIT - item["calls_today"])
    return {"valid": True, "tier": "free", "calls_remaining": remaining}
```

- [ ] Run: `pytest tests/test_db.py -v`
- [ ] Expected: All PASS

- [ ] Commit:
```bash
git add xbridge_mcp/db.py xbridge_mcp/migrations/ tests/test_db.py pyproject.toml
git commit -m "feat: add SQLite db layer (replaces DynamoDB)"
```

---

## Task 2: Resend email module

**Files:**
- Create: `xbridge_mcp/email_sender.py`
- Create: `tests/test_email_sender.py`

### Step 2.1 — Write failing test

- [ ] Create `tests/test_email_sender.py`:

```python
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from xbridge_mcp.email_sender import send_key_email


@pytest.mark.asyncio
async def test_send_free_key_email():
    mock_response = MagicMock()
    mock_response.status_code = 200
    with patch("xbridge_mcp.email_sender._client") as mock_client:
        mock_client.post = AsyncMock(return_value=mock_response)
        await send_key_email("user@example.com", "test-key-123", "free")
        mock_client.post.assert_called_once()
        call_json = mock_client.post.call_args[1]["json"]
        assert call_json["to"] == ["user@example.com"]
        assert "test-key-123" in call_json["text"]


@pytest.mark.asyncio
async def test_send_paid_key_email():
    mock_response = MagicMock()
    mock_response.status_code = 200
    with patch("xbridge_mcp.email_sender._client") as mock_client:
        mock_client.post = AsyncMock(return_value=mock_response)
        await send_key_email("pro@example.com", "paid-key-456", "paid")
        call_json = mock_client.post.call_args[1]["json"]
        assert "Pro" in call_json["subject"]
        assert "paid-key-456" in call_json["text"]
```

- [ ] Run: `pytest tests/test_email_sender.py -v`
- [ ] Expected: FAIL with `ModuleNotFoundError`

### Step 2.2 — Implement email_sender.py

- [ ] Create `xbridge_mcp/email_sender.py`:

```python
import os
import logging
import httpx

log = logging.getLogger(__name__)

_RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")
_FROM = os.environ.get("EMAIL_FROM", "hello@xbridgemcp.com")
_RESEND_URL = "https://api.resend.com/emails"

_client = httpx.AsyncClient(timeout=10.0)


async def send_key_email(to: str, key: str, tier: str) -> None:
    if not _RESEND_API_KEY:
        log.warning("RESEND_API_KEY not set — skipping email to %s", to)
        return

    if tier == "paid":
        subject = "Your xBridge MCP Pro key"
        text = (
            f"Welcome to xBridge MCP Pro!\n\n"
            f"Your unlimited API key:\n\n"
            f"  XBRIDGE_KEY={key}\n\n"
            f"Add it to your MCP config and restart your client.\n\n"
            f"Setup guide: https://xbridgemcp.com/guide\n"
            f"Support: hello@xbridgemcp.com\n"
        )
    else:
        subject = "Your xBridge MCP free key"
        text = (
            f"Here's your xBridge MCP free key (50 calls/day):\n\n"
            f"  XBRIDGE_KEY={key}\n\n"
            f"Add it to your MCP config and restart your client.\n\n"
            f"Upgrade to Pro for unlimited: https://xbridgemcp.com/pro\n"
        )

    try:
        resp = await _client.post(
            _RESEND_URL,
            headers={"Authorization": f"Bearer {_RESEND_API_KEY}"},
            json={"from": _FROM, "to": [to], "subject": subject, "text": text},
        )
        if resp.status_code not in (200, 201):
            log.error("Resend failed (%s): %s", resp.status_code, resp.text)
    except Exception as e:
        log.error("Email send failed for %s: %s", to, e)
```

- [ ] Run: `pytest tests/test_email_sender.py -v`
- [ ] Expected: All PASS

- [ ] Commit:
```bash
git add xbridge_mcp/email_sender.py tests/test_email_sender.py
git commit -m "feat: add Resend email sender (replaces SES)"
```

---

## Task 3: Per-request API key isolation (auth.py)

**Files:**
- Create: `xbridge_mcp/auth.py`
- Create: `tests/test_auth.py`

### Step 3.1 — Write failing test

- [ ] Create `tests/test_auth.py`:

```python
import asyncio
import pytest
from xbridge_mcp.auth import set_request_keys, get_xai_api_key, get_xbridge_key


@pytest.mark.asyncio
async def test_key_isolation_between_coroutines():
    """Two concurrent coroutines must not see each other's keys."""
    results = {}

    async def worker(name: str, xai_key: str, xbridge_key: str):
        async with set_request_keys(xai_key=xai_key, xbridge_key=xbridge_key):
            await asyncio.sleep(0.01)  # yield to other coroutines
            results[name] = {
                "xai": get_xai_api_key(),
                "xbridge": get_xbridge_key(),
            }

    await asyncio.gather(
        worker("alice", "xai-alice", "xbrdg-alice"),
        worker("bob", "xai-bob", "xbrdg-bob"),
    )

    assert results["alice"]["xai"] == "xai-alice"
    assert results["bob"]["xai"] == "xai-bob"
    assert results["alice"]["xbridge"] == "xbrdg-alice"
    assert results["bob"]["xbridge"] == "xbrdg-bob"


@pytest.mark.asyncio
async def test_get_xai_api_key_raises_without_context():
    with pytest.raises(ValueError, match="XAI_API_KEY"):
        get_xai_api_key()


@pytest.mark.asyncio
async def test_get_xbridge_key_returns_none_without_context():
    assert get_xbridge_key() is None
```

- [ ] Run: `pytest tests/test_auth.py -v`
- [ ] Expected: FAIL with `ModuleNotFoundError`

### Step 3.2 — Implement auth.py

- [ ] Create `xbridge_mcp/auth.py`:

```python
import os
from contextvars import ContextVar
from contextlib import asynccontextmanager
from typing import AsyncGenerator

_xai_api_key_var: ContextVar[str | None] = ContextVar("xai_api_key", default=None)
_xbridge_key_var: ContextVar[str | None] = ContextVar("xbridge_key", default=None)


@asynccontextmanager
async def set_request_keys(
    xai_key: str | None = None, xbridge_key: str | None = None
) -> AsyncGenerator[None, None]:
    xai_token = _xai_api_key_var.set(xai_key or os.environ.get("XAI_API_KEY"))
    xbridge_token = _xbridge_key_var.set(xbridge_key)
    try:
        yield
    finally:
        _xai_api_key_var.reset(xai_token)
        _xbridge_key_var.reset(xbridge_token)


def get_xai_api_key() -> str:
    key = _xai_api_key_var.get()
    if not key:
        raise ValueError(
            "XAI_API_KEY not set. Pass x-xai-api-key header or set XAI_API_KEY env var."
        )
    return key


def get_xbridge_key() -> str | None:
    return _xbridge_key_var.get()
```

- [ ] Run: `pytest tests/test_auth.py -v`
- [ ] Expected: All PASS

- [ ] Commit:
```bash
git add xbridge_mcp/auth.py tests/test_auth.py
git commit -m "feat: add per-request API key isolation via contextvars"
```

---

## Task 4: Extract tool handlers into tools.py

**Files:**
- Create: `xbridge_mcp/tools.py`
- Modify: `xbridge_mcp/server.py` (remove handler functions, keep list_tools + call_tool dispatcher)

### Step 4.1 — Extract tool logic

- [ ] In `xbridge_mcp/server.py`, find all `handle_grok_*` async functions (search for `async def handle_grok_`). There are ~19 of them.

- [ ] Create `xbridge_mcp/tools.py` and move ALL `handle_grok_*` functions there verbatim. Also move these constants and helpers:
  - `make_grok_request()`
  - `get_api_key()` — **update this** to call `auth.get_xai_api_key()` instead of `os.environ.get`:

```python
# In tools.py
from .auth import get_xai_api_key as _get_xai_api_key

def get_api_key() -> str:
    return _get_xai_api_key()
```

- [ ] Add import at top of `tools.py`:
```python
from __future__ import annotations
import os, json, base64, asyncio, logging
from typing import Optional, Any
import httpx
from pathlib import Path
from mcp.types import TextContent, ImageContent, CallToolResult
from .session_manager import get_session_manager
from .tool_chains import ChainBuilder
from .auth import get_xai_api_key as _get_xai_api_key
```

- [ ] In `server.py`, replace the moved functions with imports:
```python
from .tools import (
    handle_grok_chat, handle_grok_web_search, handle_grok_x_search,
    handle_grok_models, handle_grok_session_create, handle_grok_session_chat,
    handle_grok_session_get, handle_grok_session_list, handle_grok_session_delete,
    handle_grok_chain_search_summarize, handle_grok_chain_research,
    handle_grok_chain_debug, handle_grok_image_generate, handle_grok_image_edit,
    handle_grok_image_models, handle_grok_video_generate,
    handle_grok_docs_list, handle_grok_docs_get, handle_grok_docs_search,
)
```

- [ ] Run existing tests to verify nothing broke:
```bash
pytest tests/ -v --ignore=tests/test_db.py --ignore=tests/test_auth.py --ignore=tests/test_email_sender.py
```
- [ ] Expected: All existing tests PASS

- [ ] Commit:
```bash
git add xbridge_mcp/tools.py xbridge_mcp/server.py
git commit -m "refactor: extract tool handlers into tools.py"
```

---

## Task 5: HTTP server (FastMCP + Streamable HTTP)

**Files:**
- Create: `xbridge_mcp/http_server.py`
- Create: `tests/test_http_server.py`

### Step 5.1 — Write failing smoke test

- [ ] Create `tests/test_http_server.py`:

```python
import pytest
from httpx import AsyncClient, ASGITransport
from xbridge_mcp.http_server import build_app


@pytest.mark.asyncio
async def test_health_endpoint():
    app = build_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_mcp_endpoint_rejects_missing_key():
    app = build_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/mcp",
            json={
                "jsonrpc": "2.0",
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-03-26",
                    "capabilities": {},
                    "clientInfo": {"name": "test", "version": "1.0"},
                },
                "id": 1,
            },
            headers={"Content-Type": "application/json", "Accept": "application/json"},
        )
    # No x-xai-api-key header — should return 400
    assert resp.status_code == 400
```

- [ ] Run: `pytest tests/test_http_server.py -v`
- [ ] Expected: FAIL with `ModuleNotFoundError`

### Step 5.2 — Implement http_server.py

- [ ] Create `xbridge_mcp/http_server.py`:

```python
import logging
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route, Mount
from starlette.middleware.base import BaseHTTPMiddleware
from mcp.server.fastmcp import FastMCP

from .auth import set_request_keys
from .tools import (
    handle_grok_chat, handle_grok_web_search, handle_grok_x_search,
    handle_grok_models, handle_grok_session_create, handle_grok_session_chat,
    handle_grok_session_get, handle_grok_session_list, handle_grok_session_delete,
    handle_grok_chain_search_summarize, handle_grok_chain_research,
    handle_grok_chain_debug, handle_grok_image_generate, handle_grok_image_edit,
    handle_grok_image_models, handle_grok_video_generate,
    handle_grok_docs_list, handle_grok_docs_get, handle_grok_docs_search,
    AVAILABLE_MODELS, DEFAULT_MODEL,
)

log = logging.getLogger(__name__)


class KeyInjectionMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path == "/mcp":
            xai_key = request.headers.get("x-xai-api-key")
            if not xai_key:
                return JSONResponse(
                    {"error": "x-xai-api-key header required"}, status_code=400
                )
            xbridge_key = request.headers.get("x-xbridge-key")
            async with set_request_keys(xai_key=xai_key, xbridge_key=xbridge_key):
                return await call_next(request)
        return await call_next(request)


def _build_mcp() -> FastMCP:
    mcp = FastMCP(
        "xbridge-mcp",
        stateless_http=True,
        streamable_http_path="/mcp",
    )

    @mcp.tool(description="Send a message to Grok and get a response")
    async def grok_chat(message: str, model: str = DEFAULT_MODEL,
                        system_prompt: str = "") -> str:
        result = await handle_grok_chat({
            "message": message, "model": model, "system_prompt": system_prompt
        })
        return _extract_text(result)

    @mcp.tool(description="Search the web using Grok's live search")
    async def grok_web_search(query: str, model: str = DEFAULT_MODEL,
                               max_results: int = 5) -> str:
        result = await handle_grok_web_search({
            "query": query, "model": model, "max_results": max_results
        })
        return _extract_text(result)

    @mcp.tool(description="Search X (Twitter) posts")
    async def grok_x_search(query: str, model: str = DEFAULT_MODEL,
                             max_results: int = 10) -> str:
        result = await handle_grok_x_search({
            "query": query, "model": model, "max_results": max_results
        })
        return _extract_text(result)

    @mcp.tool(description="List available Grok models")
    async def grok_models() -> str:
        result = await handle_grok_models({})
        return _extract_text(result)

    @mcp.tool(description="Create a persistent chat session")
    async def grok_session_create(session_id: str, system_prompt: str = "") -> str:
        result = await handle_grok_session_create({
            "session_id": session_id, "system_prompt": system_prompt
        })
        return _extract_text(result)

    @mcp.tool(description="Send a message in an existing session")
    async def grok_session_chat(session_id: str, message: str,
                                 model: str = DEFAULT_MODEL) -> str:
        result = await handle_grok_session_chat({
            "session_id": session_id, "message": message, "model": model
        })
        return _extract_text(result)

    @mcp.tool(description="Get session history")
    async def grok_session_get(session_id: str) -> str:
        result = await handle_grok_session_get({"session_id": session_id})
        return _extract_text(result)

    @mcp.tool(description="List all sessions")
    async def grok_session_list() -> str:
        result = await handle_grok_session_list({})
        return _extract_text(result)

    @mcp.tool(description="Delete a session")
    async def grok_session_delete(session_id: str) -> str:
        result = await handle_grok_session_delete({"session_id": session_id})
        return _extract_text(result)

    @mcp.tool(description="Search then summarize results in one step")
    async def grok_chain_search_summarize(query: str, model: str = DEFAULT_MODEL) -> str:
        result = await handle_grok_chain_search_summarize({
            "query": query, "model": model
        })
        return _extract_text(result)

    @mcp.tool(description="Multi-step research chain")
    async def grok_chain_research(topic: str, model: str = DEFAULT_MODEL) -> str:
        result = await handle_grok_chain_research({"topic": topic, "model": model})
        return _extract_text(result)

    @mcp.tool(description="Debug code with Grok")
    async def grok_chain_debug(code: str, error: str = "",
                                model: str = DEFAULT_MODEL) -> str:
        result = await handle_grok_chain_debug({
            "code": code, "error": error, "model": model
        })
        return _extract_text(result)

    @mcp.tool(description="Generate an image with Grok")
    async def grok_image_generate(prompt: str, model: str = "grok-imagine-image",
                                   aspect_ratio: str = "1:1") -> str:
        result = await handle_grok_image_generate({
            "prompt": prompt, "model": model, "aspect_ratio": aspect_ratio
        })
        return _extract_text(result)

    @mcp.tool(description="Edit an image with Grok")
    async def grok_image_edit(prompt: str, image_url: str = "",
                               image_base64: str = "") -> str:
        result = await handle_grok_image_edit({
            "prompt": prompt, "image_url": image_url, "image_base64": image_base64
        })
        return _extract_text(result)

    @mcp.tool(description="List available image models")
    async def grok_image_models() -> str:
        result = await handle_grok_image_models({})
        return _extract_text(result)

    @mcp.tool(description="Generate a video with Grok")
    async def grok_video_generate(prompt: str, model: str = "grok-imagine-video",
                                   aspect_ratio: str = "16:9") -> str:
        result = await handle_grok_video_generate({
            "prompt": prompt, "model": model, "aspect_ratio": aspect_ratio
        })
        return _extract_text(result)

    @mcp.tool(description="List xAI documentation pages")
    async def grok_docs_list() -> str:
        result = await handle_grok_docs_list({})
        return _extract_text(result)

    @mcp.tool(description="Get a specific xAI documentation page")
    async def grok_docs_get(slug: str) -> str:
        result = await handle_grok_docs_get({"slug": slug})
        return _extract_text(result)

    @mcp.tool(description="Search xAI documentation")
    async def grok_docs_search(query: str, limit: int = 5) -> str:
        result = await handle_grok_docs_search({"query": query, "limit": limit})
        return _extract_text(result)

    return mcp


def _extract_text(result) -> str:
    if isinstance(result, list):
        return "\n".join(
            c.text if hasattr(c, "text") else str(c) for c in result
        )
    return str(result)


def build_app() -> Starlette:
    mcp = _build_mcp()
    mcp_app = mcp.streamable_http_app()

    async def health(request: Request):
        return JSONResponse({"status": "ok", "version": "3.0.0"})

    app = Starlette(
        routes=[
            Route("/health", health),
            Mount("/", app=mcp_app),
        ],
    )
    app.add_middleware(KeyInjectionMiddleware)
    return app
```

- [ ] Run: `pytest tests/test_http_server.py -v`
- [ ] Expected: All PASS

- [ ] Commit:
```bash
git add xbridge_mcp/http_server.py tests/test_http_server.py
git commit -m "feat: add FastMCP Streamable HTTP server with key injection middleware"
```

---

## Task 6: Update key_validator.py (inline SQLite validation)

**Files:**
- Modify: `xbridge_mcp/key_validator.py`

### Step 6.1 — Rewrite key_validator.py

The current `key_validator.py` makes an HTTP call to `api.xbridgemcp.com`. In the remote server, validation is local (same process, same SQLite). Replace with direct db call.

- [ ] Read current `xbridge_mcp/key_validator.py` then replace:

```python
import time
from .auth import get_xbridge_key
from .db import get_key, try_increment_free

_CACHE_TTL = 60.0
_cache: dict = {}


async def validate_request() -> dict:
    """Validate the current request's XBRIDGE_KEY (from contextvars)."""
    key = get_xbridge_key()
    if not key:
        return {"valid": True, "tier": "self-hosted"}

    now = time.monotonic()
    cached = _cache.get(key)
    if cached and (now - cached["ts"]) < _CACHE_TTL:
        return {k: v for k, v in cached.items() if k != "ts"}

    item = await get_key(key)
    if not item:
        return {"valid": False}

    if item["tier"] == "paid":
        result = {"valid": True, "tier": "paid", "calls_remaining": None}
    else:
        result = await try_increment_free(key)

    _cache[key] = {**result, "ts": now}
    return result
```

Note: The old `validate(key)` function signature was used in `server.py`. Update any calls in `server.py` and `tools.py` from `await _validate_key(key)` to `await validate_request()`.

- [ ] Search for all usages: `grep -n "_validate_key\|validate_request\|key_validator" xbridge_mcp/server.py xbridge_mcp/tools.py`

- [ ] Update each call site to use `from .key_validator import validate_request` and call `await validate_request()`.

- [ ] Run all tests: `pytest tests/ -v`
- [ ] Expected: All PASS

- [ ] Commit:
```bash
git add xbridge_mcp/key_validator.py xbridge_mcp/server.py xbridge_mcp/tools.py
git commit -m "refactor: inline key validation via SQLite (removes AWS round-trip)"
```

---

## Task 7: Session namespacing for multi-user safety

**Files:**
- Modify: `xbridge_mcp/session_manager.py`

### Step 7.1 — Namespace sessions by key hash

Currently sessions use raw `session_id` strings as filenames. In remote mode, two users could collide if they use the same session_id (e.g., `"default"`).

- [ ] Read `xbridge_mcp/session_manager.py` and find where session file paths are constructed.

- [ ] Add a namespacing function:

```python
import hashlib
from .auth import get_xbridge_key, get_xai_api_key

def _session_prefix() -> str:
    """Return a short hash of the current user's key for session namespacing."""
    try:
        key = get_xbridge_key() or get_xai_api_key()
    except ValueError:
        return "local"
    return hashlib.sha256(key.encode()).hexdigest()[:12]

def _namespaced_session_id(session_id: str) -> str:
    return f"{_session_prefix()}_{session_id}"
```

- [ ] Update every place that builds a session file path to use `_namespaced_session_id(session_id)` instead of raw `session_id`.

- [ ] Run all tests: `pytest tests/ -v`
- [ ] Expected: All PASS

- [ ] Commit:
```bash
git add xbridge_mcp/session_manager.py
git commit -m "fix: namespace sessions by user key hash (multi-user safety)"
```

---

## Task 8: Add HTTP entry point to pyproject.toml + server

**Files:**
- Modify: `pyproject.toml`
- Modify: `xbridge_mcp/server.py`

### Step 8.1 — Add http entry point and bump version

- [ ] Edit `pyproject.toml`:

```toml
version = "3.0.0"

[project.scripts]
xbridge-mcp = "xbridge_mcp.server:run"
xbridge-mcp-http = "xbridge_mcp.server:run_http"
```

### Step 8.2 — Add run_http() to server.py

- [ ] Add to the bottom of `xbridge_mcp/server.py`:

```python
def run_http():
    """Run xBridge MCP as a Streamable HTTP server (remote mode)."""
    import uvicorn
    from .http_server import build_app

    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8000"))
    app = build_app()
    uvicorn.run(app, host=host, port=port)
```

- [ ] Add uvicorn to dependencies in `pyproject.toml`:

```toml
dependencies = [
    "mcp>=1.0.0",
    "httpx>=0.27.0",
    "aiosqlite>=0.20.0",
    "uvicorn>=0.30.0",
]
```

- [ ] Install: `pip install uvicorn`

- [ ] Test locally:
```bash
XAI_API_KEY=test xbridge-mcp-http &
curl http://localhost:8000/health
# Expected: {"status": "ok", "version": "3.0.0"}
kill %1
```

- [ ] Commit:
```bash
git add pyproject.toml xbridge_mcp/server.py
git commit -m "feat: add xbridge-mcp-http entry point (Streamable HTTP mode)"
```

---

## Task 9: VPS deployment

**Files:**
- Create: `deploy/xbridge.service`
- Create: `deploy/nginx-mcp.conf`

### Step 9.1 — systemd service

- [ ] Create `deploy/xbridge.service`:

```ini
[Unit]
Description=xBridge MCP HTTP Server
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/xbridge-mcp
Environment="HOST=127.0.0.1"
Environment="PORT=8000"
Environment="XBRIDGE_DB_PATH=/opt/xbridge-mcp/data/keys.db"
EnvironmentFile=/opt/xbridge-mcp/.env
ExecStart=/opt/xbridge-mcp/venv/bin/xbridge-mcp-http
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

### Step 9.2 — nginx config

- [ ] Create `deploy/nginx-mcp.conf`:

```nginx
server {
    listen 80;
    server_name mcp.xbridgemcp.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl;
    server_name mcp.xbridgemcp.com;

    ssl_certificate /etc/letsencrypt/live/mcp.xbridgemcp.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/mcp.xbridgemcp.com/privkey.pem;

    # Required for SSE / streaming responses
    proxy_buffering off;
    proxy_read_timeout 600s;
    proxy_send_timeout 600s;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header Connection "";
    }
}
```

### Step 9.3 — Deploy to VPS

Run these on the VPS (`ssh user@168.231.109.225`):

- [ ]
```bash
# Install app
git clone git@github.com:hrco/xbridge-mcp.git /opt/xbridge-mcp
cd /opt/xbridge-mcp
python3 -m venv venv
venv/bin/pip install -e ".[dev]"

# Create data dir
mkdir -p /opt/xbridge-mcp/data

# Create .env
cat > /opt/xbridge-mcp/.env << 'EOF'
RESEND_API_KEY=your_resend_key_here
EMAIL_FROM=hello@xbridgemcp.com
EOF

# Init DB
venv/bin/python -c "import asyncio; from xbridge_mcp.db import init_db; asyncio.run(init_db())"

# Install cert
certbot certonly --nginx -d mcp.xbridgemcp.com

# Install nginx config
cp deploy/nginx-mcp.conf /etc/nginx/sites-available/mcp.xbridgemcp.com
ln -s /etc/nginx/sites-available/mcp.xbridgemcp.com /etc/nginx/sites-enabled/
nginx -t && systemctl reload nginx

# Install systemd service
cp deploy/xbridge.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable xbridge
systemctl start xbridge
systemctl status xbridge
```

- [ ] Verify live:
```bash
curl https://mcp.xbridgemcp.com/health
# Expected: {"status": "ok", "version": "3.0.0"}
```

- [ ] Test MCP endpoint with a key:
```bash
curl -X POST https://mcp.xbridgemcp.com/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -H "x-xai-api-key: $XAI_API_KEY" \
  -d '{"jsonrpc":"2.0","method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}},"id":1}'
# Expected: JSON with serverInfo
```

- [ ] Commit:
```bash
git add deploy/
git commit -m "chore: add VPS deployment files (systemd + nginx)"
```

---

## Task 10: Point LemonSqueezy webhook to VPS

This is the cut-over step. Do this ONLY after Task 9 is verified live.

### Step 10.1 — Add webhook handler to http_server.py

The LemonSqueezy webhook currently hits the AWS Lambda. We need the same logic on the VPS.

- [ ] Add to `xbridge_mcp/http_server.py`:

```python
import hmac, hashlib, json, logging
from starlette.requests import Request
from starlette.responses import Response
from .db import create_key, extend_paid_key, downgrade_key, get_key_by_sub_id
from .email_sender import send_key_email

_LS_SECRET = os.environ.get("LS_SIGNING_SECRET", "").encode()


async def webhook_ls(request: Request) -> Response:
    body = await request.body()

    if _LS_SECRET:
        sig = request.headers.get("x-signature", "")
        expected = hmac.new(_LS_SECRET, body, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, sig):
            return Response("Unauthorized", status_code=401)

    payload = json.loads(body)
    event = payload.get("meta", {}).get("event_name", "")
    data = payload.get("data", {})
    attrs = data.get("attributes", {})
    sub_id = str(data.get("id", ""))

    log.info("LS event: %s sub_id: %s", event, sub_id)

    if event == "subscription_created":
        email = attrs.get("user_email", "")
        existing = await get_key_by_sub_id(sub_id)
        key = existing["key"] if existing else await create_key(email, "paid", sub_id)
        try:
            await send_key_email(email, key, "paid")
        except Exception as e:
            log.error("Email failed for %s: %s", email, e)

    elif event == "subscription_updated" and attrs.get("status") == "active":
        await extend_paid_key(sub_id, days=30)

    elif event in ("subscription_cancelled", "subscription_expired"):
        await downgrade_key(sub_id)

    return Response("ok", status_code=200)
```

- [ ] Add `LS_SIGNING_SECRET` to `build_app()` routes:

```python
routes=[
    Route("/health", health),
    Route("/webhooks/ls", webhook_ls, methods=["POST"]),
    Mount("/", app=mcp_app),
]
```

- [ ] Add `LS_SIGNING_SECRET` to VPS `.env` file.

### Step 10.2 — Switch LemonSqueezy

- [ ] In LS dashboard → Webhooks → edit webhook URL to: `https://mcp.xbridgemcp.com/webhooks/ls`
- [ ] Send test webhook from LS dashboard
- [ ] Check VPS logs: `journalctl -u xbridge -f`
- [ ] Expected: `LS event: subscription_created sub_id: ...` in logs

- [ ] Commit:
```bash
git add xbridge_mcp/http_server.py
git commit -m "feat: add LemonSqueezy webhook handler to HTTP server"
git push origin release
```

---

## Task 11: Update site API URLs

**Files:**
- Modify: `site/index.html` (already done in previous session — verify)

The free key signup form and resend form already point to the AWS API Gateway URL (updated in a prior commit). Update them to point to the VPS.

- [ ] In `site/index.html`, replace all `https://y0xx9n1oz7.execute-api.eu-west-1.amazonaws.com` with `https://mcp.xbridgemcp.com`

- [ ] Deploy site: `bash scripts/deploy.sh 168.231.109.225`

- [ ] Add the missing key management endpoints to `http_server.py` (mirror what was on AWS):

```python
async def keys_free(request: Request) -> Response:
    import re
    from .db import email_exists, create_key
    from .email_sender import send_key_email
    EMAIL_RE = re.compile(r'^[^@]+@[^@]+\.[^@]+$')
    body = await request.json()
    email = body.get("email", "").strip().lower()
    if not EMAIL_RE.match(email):
        return JSONResponse({"error": "Invalid email"}, status_code=400)
    if await email_exists(email):
        return JSONResponse({"error": "Email already registered."}, status_code=409)
    key = await create_key(email, "free")
    try:
        await send_key_email(email, key, "free")
    except Exception as e:
        log.error("Email failed for %s: %s", email, e)
    return JSONResponse({"success": True})


async def keys_resend(request: Request) -> Response:
    import re
    from .db import get_key_by_email
    from .email_sender import send_key_email
    EMAIL_RE = re.compile(r'^[^@]+@[^@]+\.[^@]+$')
    body = await request.json()
    email = body.get("email", "").strip().lower()
    if not EMAIL_RE.match(email):
        return JSONResponse({"error": "Invalid email"}, status_code=400)
    item = await get_key_by_email(email)
    if item:
        try:
            await send_key_email(email, item["key"], item.get("tier", "free"))
        except Exception as e:
            log.error("Resend email failed for %s: %s", email, e)
    return JSONResponse({"success": True, "message": "If that email is registered, your key is on its way."})


async def keys_usage(request: Request) -> Response:
    from datetime import datetime, timezone
    from .db import get_key
    body = await request.json()
    key = body.get("key", "").strip()
    if not key:
        return JSONResponse({"error": "key required"}, status_code=400)
    item = await get_key(key)
    if not item:
        return JSONResponse({"valid": False})
    tier = item.get("tier", "free")
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    calls_today = item.get("calls_today", 0) if item.get("call_date") == today else 0
    if tier == "paid":
        return JSONResponse({"valid": True, "tier": "paid", "calls_today": calls_today, "calls_remaining": None})
    return JSONResponse({"valid": True, "tier": "free", "calls_today": calls_today,
                         "calls_remaining": max(0, 50 - calls_today), "daily_limit": 50})
```

- [ ] Add routes:
```python
Route("/keys/free", keys_free, methods=["POST"]),
Route("/keys/resend", keys_resend, methods=["POST"]),
Route("/keys/usage", keys_usage, methods=["POST"]),
```

- [ ] Commit:
```bash
git add xbridge_mcp/http_server.py site/index.html
git commit -m "feat: add /keys/free, /keys/resend, /keys/usage to HTTP server"
```

---

## Task 12: Decommission AWS

**Do this only after:** VPS is live, LS webhook is switched, site URLs are updated, at least 24h of stable operation.

### Step 12.1 — Export DynamoDB data (safety net)

```bash
aws dynamodb scan --table-name xbridge_keys --region eu-west-1 \
  --output json > /tmp/dynamo_backup_$(date +%Y%m%d).json
```

### Step 12.2 — Delete CloudFormation stack

```bash
aws cloudformation delete-stack \
  --stack-name xbridge-mcp-payment \
  --region eu-west-1

# Monitor until complete (~3 min)
aws cloudformation wait stack-delete-complete \
  --stack-name xbridge-mcp-payment \
  --region eu-west-1

echo "Stack deleted"
```

### Step 12.3 — Clean up remaining AWS resources

```bash
# Remove SES identities (optional — they're free)
aws sesv2 delete-email-identity --email-identity hello@xbridgemcp.com --region eu-west-1
aws sesv2 delete-email-identity --email-identity valentin.krizan@gmail.com --region eu-west-1

# Delete the SAM deployment S3 bucket artifacts (optional)
# aws s3 rm s3://aws-sam-cli-managed-default-samclisourcebucket-dx792ecap7ww --recursive
```

### Step 12.4 — Archive aws/ directory

```bash
# Keep for reference but signal it's retired
echo "# RETIRED — replaced by VPS FastAPI deployment (2026-03-30)" > aws/README.md
git add aws/README.md
git commit -m "chore: retire AWS backend — migrated to VPS"
```

### Step 12.5 — Update DEPLOY.md in aws/

- [ ] Update `aws/DEPLOY.md` to add a `## STATUS: RETIRED` note at the top.
- [ ] Remove the live credentials from `aws/DEPLOY.md` and replace with placeholders (they're invalidated now anyway).

---

## Task 13: Update README

**Files:**
- Modify: `README.md`

### Step 13.1 — Update installation instructions

- [ ] Replace the current MCP config section with:

```markdown
## Quick Start

### Remote (recommended — no install needed)

Add to your MCP client config:

```json
{
  "mcpServers": {
    "xbridge": {
      "url": "https://mcp.xbridgemcp.com/mcp",
      "headers": {
        "x-xai-api-key": "your_xai_key_here",
        "x-xbridge-key": "your_xbridge_key_here"
      }
    }
  }
}
```

Get your free `XBRIDGE_KEY` at [xbridgemcp.com](https://xbridgemcp.com).

### Local / Self-hosted (stdio)

```bash
pip install xbridge-mcp
# or: docker pull nexuswedge/xbridge-mcp:latest
```

```json
{
  "mcpServers": {
    "xbridge": {
      "command": "xbridge-mcp",
      "env": {
        "XAI_API_KEY": "your_xai_key_here",
        "XBRIDGE_KEY": "your_xbridge_key_here"
      }
    }
  }
}
```
```

- [ ] Bump version references to 3.0.0

- [ ] Commit:
```bash
git add README.md
git commit -m "docs: update README for v3 remote MCP server"
git push origin release
```

---

## Self-Review

**Spec coverage:**
- [x] Streamable HTTP transport via FastMCP — Task 5
- [x] Per-request key isolation via contextvars — Task 3
- [x] SQLite replaces DynamoDB — Task 1
- [x] Resend replaces SES — Task 2
- [x] stdio mode preserved — Task 8 (run_http separate from run)
- [x] Session namespacing — Task 7
- [x] LemonSqueezy webhook on VPS — Task 10
- [x] /keys/free, /keys/resend, /keys/usage on VPS — Task 11
- [x] AWS decommission — Task 12
- [x] Site URLs updated — Task 11
- [x] README updated — Task 13

**No placeholders found.**

**Type consistency:**
- `create_key(email, tier, subscription_id, db_path)` — consistent across db.py and callers
- `send_key_email(to, key, tier)` — consistent across email_sender.py and callers
- `validate_request()` → replaces `validate(key)` — update all call sites in Task 6
- `set_request_keys(xai_key, xbridge_key)` — consistent across auth.py and http_server.py middleware
