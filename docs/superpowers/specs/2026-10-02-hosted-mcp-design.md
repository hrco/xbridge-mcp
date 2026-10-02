# xBridge Cloud — Hosted Remote MCP (paid tier)

> **Design spec**, 2026-10-02. Branch `feat/hosted-mcp` (from `release`).
> Goal: give the €2/€4 Pro price something real to sell: a hosted MCP endpoint that needs
> no Python/Docker install. The OSS server stays MIT and unlimited when self-hosted.

## Why

- The site sells Pro "unlimited calls" via live LemonSqueezy checkouts, but the limit lives in
  the OSS client (`_check_rate_limit`): unset `XBRIDGE_KEY` and calls are unlimited. Pro buys
  nothing a free user lacks.
- A hosted endpoint is the first place a paywall is real: the server, not the client, counts.
- The licensing backend already exists (`http_server.py`: LemonSqueezy webhook, Ed25519
  `xbrdg_v1` keys, founder cap, `/keys/free|resend|mine`). We reuse it, not rebuild it.

## Decisions

1. **Product:** hosted remote MCP at `https://mcp.xbridgemcp.com/mcp`, Streamable HTTP transport.
2. **BYOK by header, never stored.** Client sends
   `Authorization: Bearer xbrdg_v1…` (xBridge key) and `X-XAI-Key: xai-…` (their xAI key)
   on every request. The xAI key lives only for that request. Never logged, never persisted.
3. **Tiers (server-enforced):** `free` key → 50 tool calls/day (existing `check_free_limit`);
   `pro`/`founder` → unlimited. No key → 401. Self-host OSS → unchanged, unlimited.
4. **Revocation:** LemonSqueezy `subscription_expired` (end of the paid period; cancel alone keeps access until then) marks the key
   revoked in `issued_keys.json`, kept in an append-only `revoked_history` across re-subscribes; hosted auth rejects revoked keys. (Today a Pro key is valid
   365 days even after cancelling.)
5. **Stateless transport:** `StreamableHTTPSessionManager(app=server, stateless=True,
   json_response=True)`. No server-side MCP sessions to leak memory on a small VPS.
6. **Dependency pin:** `mcp>=1.8,<2`. `mcp` 2.x removed `Server.list_tools`; with the current
   unpinned floor a fresh install collects 7 test errors. Fixing this is part of shipping.

## Architecture

```
Claude Code / Cursor ──HTTPS──▶ nginx mcp.xbridgemcp.com (certbot, proxy_buffering off)
                                   ▼
                     xbridge-cloud  (uvicorn, 127.0.0.1:8787, systemd)
                     ├─ /mcp            auth middleware → StreamableHTTPSessionManager → server
                     ├─ /webhooks/ls, /keys/*, /founder-status, /health   (existing routes)
                     └─ data: XBRIDGE_DB_PATH=/opt/xbridge-mcp/data (issued_keys, free_usage)
```

### Units

| Unit | File | Does | Depends on |
|------|------|------|-----------|
| Request key lookup | `server.py` `get_api_key()` | Returns `X-XAI-Key` from the current MCP request if present, else `XAI_API_KEY` env | `server.request_context.request` |
| Auth decision | `xbridge_mcp/cloud_auth.py` | Pure fn `authorize(headers: Mapping[str,str], revoked: set[str]) -> AuthResult(ok, status, error, tier, identity)` | `tokenizer.validate_key`, `check_free_limit` |
| Revocation | `http_server.py` | Webhook handles expire (append-only history); `revoked_keys() -> set[str]` | `issued_keys.json` |
| Cloud app | `xbridge_mcp/cloud.py` | Starlette app: existing routes + `/mcp` mount behind auth; lifespan runs session manager; `main()` → uvicorn | all of the above |
| Packaging | `pyproject.toml` | `[cloud]` extra (starlette, uvicorn), script `xbridge-cloud = xbridge_mcp.cloud:main` | — |
| Deploy files | `deploy/` | systemd unit, nginx site, runbook with human-run commands | — |
| Site + README | `site/`, `README.md` | Honest pricing, hosted setup snippet, live `/keys/*` URL | — |

**Critical constraint (verified against mcp 1.30 source):** in stateless mode the SDK runs the
server inside the session manager's long-lived task group, so a `contextvars.ContextVar` set in
middleware does **not** reach tool handlers. `get_api_key()` must read
`server.request_context.request.headers` (catch `LookupError`/`AttributeError` → fall back to env).

### Auth rules (`authorize`)

| Condition | Result |
|-----------|--------|
| No `Authorization: Bearer xbrdg_v1.*` | 401 `missing xBridge key` |
| `validate_key` invalid / expired | 401 with reason |
| key in revoked set | 403 `subscription ended` |
| No `X-XAI-Key`, or not starting `xai-` | 400 `missing X-XAI-Key header` |
| tier `free` and `check_free_limit` false | 429 `free tier limit reached (50/day)` |
| otherwise | ok, `tier` set |

Only `POST` tool-call traffic counts toward the free limit. MCP `initialize`/`tools/list` must not
burn calls, so the counter runs when the JSON-RPC body's `method == "tools/call"`. Errors are JSON
`{"error": "..."}` and never echo either header value.

## Error handling

- xAI 401 from the user's key: surfaced as the tool's existing error text (no change).
- Missing data dir: created on startup (existing behaviour in `http_server.py`).
- Logs: uvicorn access log only; no header logging anywhere. A test asserts the xAI key never
  appears in captured logs or responses.

## Testing (gate)

`.claude/gate.sh` → `.venv/bin/python -m pytest -q`. All new tests mock httpx, never hit xAI.
Test signing keys: generate an Ed25519 pair in the test and monkeypatch `tokenizer._public_key`.
- `cloud_auth`: every row of the auth table.
- `get_api_key`: header beats env; env fallback outside a request.
- Revocation: expire webhook (valid signature) → key revoked → `authorize` 403; old key stays revoked after re-subscribe; cancel alone does not revoke.
- `cloud.py`: Starlette `TestClient`, 401 without key; valid pro key + `initialize` → 200;
  `tools/list` lists 21 tools; free key 51st `tools/call` → 429.

## Out of scope (v2)

Stored encrypted xAI keys + dashboard, OAuth for claude.ai connectors, Team seats, metered
billing, $XBRDG wallet verification.

## Human-only steps (red lines)

DNS `A mcp → 76.13.48.186`; VPS deploy + certbot; LemonSqueezy: pause or retitle the current
products until hosted is live, set the webhook URL to `https://mcp.xbridgemcp.com/webhooks/ls`
and enable `subscription_created` + `subscription_expired` events. Exact commands go in `docs/hosted-runbook.md`.
