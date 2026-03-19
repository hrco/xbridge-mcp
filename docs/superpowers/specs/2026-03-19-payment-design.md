# xBridge MCP — Freemium Payment System Design
Date: 2026-03-19

## Context
xBridge MCP is a Python MCP server (pip-installable, open source) bridging Claude Code → xAI Grok API. Going public on GitHub this weekend. Zero paying customers currently. EU-based solo developer.

## Decision Summary
- **Payment platform:** LemonSqueezy (MoR, EU VAT auto-handled, battle-tested webhooks)
- **Backend:** AWS Lambda + API Gateway + DynamoDB + SES (free credits, serverless, DynamoDB TTL for key expiry)
- **Static sites:** VPS unchanged (xbridgemcp.com, xbrdg.com)
- **Grok-consulted:** Architecture validated via xBridge session 917de191

## Tiers

| Tier | Price | Gate |
|---|---|---|
| Self-hosted (OSS) | Free | None — OSS promise, no XBRIDGE_KEY needed |
| Free key | Free | 50 calls/day, from xbridgemcp.com/free signup |
| Pro — Founder | €3.69/mo | FOUNDER50 coupon, first 50 users only |
| Pro — Standard | €9/mo | After 50 founders |
| $XBRDG holder | −20% on Pro | Solana wallet verify at checkout |

## Architecture

### AWS Backend (api.xbridgemcp.com)

```
API Gateway
  POST /validate        → Lambda: validate_key
  POST /keys/free       → Lambda: create_free_key
  POST /webhooks/ls     → Lambda: webhook_handler
  POST /keys/verify-xbrdg → Lambda: xbrdg_discount
        ↓
  DynamoDB: xbridge_keys
        ↓
  SES: hello@xbridgemcp.com
```

### DynamoDB Schema (xbridge_keys)

```
PK: key (String, UUID)
tier:            "free" | "paid"
email:           String
calls_today:     Number (atomic)
call_date:       String (YYYY-MM-DD)
TTL:             Number (Unix ts, auto-expiry for paid keys)
subscription_id: String (LemonSqueezy ID)
created_at:      String (ISO)
```

### Lambda Functions

**validate_key** — hot path, called by server.py:
- GetItem by key
- If paid + not expired → {valid: true, tier: "paid"}
- If free → atomic increment calls_today, check ≤50, reset if new day
- Returns: {valid, tier, calls_remaining}

**create_free_key** — signup:
- Check email uniqueness (GSI on email)
- Generate UUID, PutItem (tier=free)
- SES send key email

**webhook_handler** — LemonSqueezy events:
- `subscription_created` → generate UUID key, tier=paid, TTL=now+30d, SES send
- `subscription_renewed` → UpdateItem TTL=now+30d
- `subscription_cancelled` → downgrade tier=free (keep key)

**xbrdg_discount** — $XBRDG holder check:
- Solana RPC: getTokenAccountBalance for CA 6vUhppYep18WSncUDR6Brt9yZw31ycLDPDEHo13pump
- If ≥1000 tokens → generate one-time LemonSqueezy coupon (20% off) via API
- Returns coupon code to checkout page

### server.py Changes (~60 LOC)

```python
XBRIDGE_KEY = os.environ.get("XBRIDGE_KEY")  # optional
_key_cache = {"valid": None, "tier": None, "remaining": None, "ts": 0}
_CACHE_TTL = 60  # seconds — avoids Lambda cold starts on every call

async def _validate_key() -> dict:
    if not XBRIDGE_KEY:
        return {"valid": True, "tier": "self-hosted"}
    # cache check → httpx POST /validate → update cache → return
```

In `call_tool()`: validate before dispatch. Rate-limited response is a TextContent with upgrade URL.

## Payment Flow

1. User visits xbridgemcp.com/pro
2. Optionally enters Solana wallet → 20% coupon generated
3. LemonSqueezy checkout with FOUNDER50 (if slots remain) + optional XBRDG coupon
4. `subscription_created` webhook → paid key generated → emailed to user
5. User adds `XBRIDGE_KEY=<key>` to their `.env`
6. server.py validates on tool calls, cached 60s

## Testing
- pytest: mock Lambda responses, test rate limit logic, test cache behavior
- LemonSqueezy test mode: simulate all webhook events before going live
- Solana RPC: use devnet for $XBRDG check testing

## Files to Create/Modify
- `xbridge_mcp/server.py` — add key validation
- `xbridge_mcp/key_validator.py` — extracted validation logic
- `aws/lambda/validate_key/handler.py`
- `aws/lambda/create_free_key/handler.py`
- `aws/lambda/webhook_handler/handler.py`
- `aws/lambda/xbrdg_discount/handler.py`
- `aws/template.yaml` — SAM deployment template
- `site/index.html` — add /free signup form + /pro checkout page
- `.env.example` — add XBRIDGE_KEY
- `tests/test_key_validator.py`
- `tests/test_webhooks.py`
