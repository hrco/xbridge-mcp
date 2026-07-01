# xBridge MCP v3.0.0 — De-AWS: Full Billing Excision

> **Design spec.** Goal: make xBridge MCP run with zero AWS dependency by removing
> the entire licensing/billing layer. xBridge becomes pure BYOK (bring your own xAI
> key), MIT, self-hosted. No keys, no tiers, no rate limits, no remote backend.

## Background

AWS is **not** part of the MCP server's core path. It is a separate licensing/billing
backend. The coupling between the two is a single `httpx.post` in
`xbridge_mcp/key_validator.py` that calls an AWS API Gateway URL to validate a paid
`XBRIDGE_KEY`. That validator already degrades to `{'valid': True, 'tier': 'self-hosted'}`
on any error or when no key is set — so the server already functions without AWS today.

This change removes the billing concept entirely rather than leaving dead plumbing.

| Layer | AWS-dependent? | Disposition |
|-------|---------------|-------------|
| `server.py` core tools (19 Grok tools) | No | Keep — only the auth guard is removed |
| `key_validator.py` | Yes (1 HTTP call) | Delete |
| `aws/` SAM stack (6 Lambdas + DynamoDB + SES + LemonSqueezy webhook) | Yes | Delete |

## Decisions (settled in brainstorming)

1. **Removal depth: full excision.** Remove `key_validator.py`, the `XBRIDGE_KEY`
   concept, and all tier-gating from `server.py`. The server has zero notion of
   keys or tiers. No backward-compat stub.
2. **`aws/` disposition: `git rm`.** Delete the entire tree from the working set.
   Git history retains it for reference.
3. **Site: out of scope.** `site/*.html` billing forms (free-key signup, resend,
   `$XBRDG` discount, `/pro` pricing) are left untouched in this pass and handled
   separately later. The dead AWS form actions remain for now.
4. **Version: 3.0.0.** Removing the `XBRIDGE_KEY` contract is a breaking change, so
   a major bump. Reconcile both `pyproject.toml` (currently 2.1.0) and the
   `CLAUDE.md` header (currently says v2.2.0) to 3.0.0.

## Scope

### Files deleted (`git rm`)

| Path | Reason |
|------|--------|
| `aws/` (whole tree) | The billing backend: 6 Lambdas, DynamoDB table, SES email, LemonSqueezy webhook. |
| `xbridge_mcp/key_validator.py` | The sole AWS coupling in the MCP server. |
| `tests/test_key_validator.py` | Tests the deleted validator. |
| `tests/test_validate_key.py` | Tests the deleted `validate_key` Lambda. |
| `tests/test_webhooks.py` | Tests the deleted LemonSqueezy webhook Lambda. |

### Files modified

**`xbridge_mcp/server.py`**
- Remove line 33: `from .key_validator import validate as _validate_key`
- Remove line 35: `_XBRIDGE_KEY = os.environ.get('XBRIDGE_KEY')`
- Remove the auth guard at the top of `call_tool` (lines 1008–1019): the
  `_validate_key` call, the `Invalid XBRIDGE_KEY` branch, and the
  `calls_remaining == 0` daily-limit branch. The `try:` block flows straight into
  `# Original tools` / `if name == "grok-chat":`.
- Line 946 comment: `# xAI Docs tools (xBridge paid tier)` → drop the
  `(xBridge paid tier)` qualifier.

Resulting `call_tool` head:
```python
async def call_tool(name: str, arguments: dict[str, Any]) -> CallToolResult:
    """Handle tool invocations."""
    try:
        # Original tools
        if name == "grok-chat":
            return await handle_grok_chat(arguments)
        ...
```

**`pyproject.toml`** — bump `version = "2.1.0"` → `version = "3.0.0"`. `httpx`
stays a dependency (used by `server.py` for Grok API calls).

**`.env.example`** — remove `XBRIDGE_KEY` and `VALIDATE_URL`. Final contents:
```
# xAI Grok API Configuration — get your key at https://x.ai/api
XAI_API_KEY=

# Optional: force USA routing (e.g. us-east-1)
XAI_REGION=
```

**`README.md`**
- Line 18 pricing table: replace the Free/Pro tier table with a one-line statement —
  free & open source, BYOK (bring your own xAI key).
- Line 62: drop `"XBRIDGE_KEY"` from the MCP config JSON example.
- Line 111: drop the `XBRIDGE_KEY` row from the env-var table.

**`CLAUDE.md`**
- Line 3 tagline: `BYOK. Paid-first.` → `BYOK. Free & open source.`
- Line 8: `Two distributions: free MIT source + paid Docker image (€3.69/mo Pro, BYOK).`
  → `MIT source + Docker image, BYOK.`
- Reconcile the version header to v3.0.0.

### Explicitly out of scope
- `site/*.html` and `xbrdg-site/` — left as-is (dead billing forms remain).
- `$XBRDG` token sections and the `XBRIDGE-*` launch/marketing agents — unrelated to
  billing; touching them drifts into site scope.
- The VPS-migration plan (`docs/superpowers/plans/2026-03-30-vps-migration.md`) — that
  was Option B (keep billing, move it to a VPS). This spec is Option A and supersedes
  it; the plan doc is left in place as a record of the road not taken.

## Verification

1. `pytest tests/ -v` → the 6 remaining test files (`test_core`, `test_docs_tools`,
   `test_image_tools`, `test_image_integration`, `test_session_manager`,
   `test_tool_chains`) all pass. None reference the validator (grep-confirmed).
2. `grep -rn "key_validator\|XBRIDGE_KEY\|_validate_key" xbridge_mcp/` → returns nothing.
3. `python -c "import xbridge_mcp.server"` → no `ImportError`.
4. `grep -rn "VALIDATE_URL\|execute-api" xbridge_mcp/ .env.example` → returns nothing
   (the runtime/config no longer points at AWS).

## Risks & notes

- **Existing users with `XBRIDGE_KEY` set:** after upgrade the env var is simply
  ignored — no error, tools work unconditionally. Documented via the 3.0.0 major bump.
- **Site forms still POST to dead AWS endpoints** until the separate site pass. Known
  and accepted per the out-of-scope decision.
- **No dependency removal needed:** `httpx` remains in use by the core server.
