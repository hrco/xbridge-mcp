# De-AWS: Full Billing Excision Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make xBridge MCP run with zero AWS dependency by removing the entire licensing/billing layer, turning it into pure BYOK (bring your own xAI key), MIT, self-hosted — bumped to v3.0.0.

**Architecture:** The billing enforcement is a single auth guard at the top of `call_tool` in `server.py`, fed by `key_validator.py` which makes one HTTP call to AWS. Remove the guard and the validator; the `try:` block then dispatches tools unconditionally. The separate `aws/` SAM stack (Lambdas + DynamoDB + SES + LemonSqueezy webhook) and its tests are deleted outright. Docs/config drop all `XBRIDGE_KEY`/tier language.

**Tech Stack:** Python 3.10+, pytest (asyncio_mode=auto), git. No new dependencies; `httpx` stays (used by core Grok calls).

**Spec:** `docs/superpowers/specs/2026-06-07-de-aws-billing-excision-design.md`

**Ordering rule:** Deletions are grouped so the repo stays green after every task — never leave an import dangling. `server.py`'s import of `key_validator` is removed in the *same* task that deletes `key_validator.py`. The two AWS-dependent tests are removed in the *same* task that deletes `aws/`.

---

## Task 1: Excise the billing guard from server.py + delete the validator

Removes the only AWS coupling inside the MCP server, in one atomic, still-green step.

**Files:**
- Modify: `xbridge_mcp/server.py` (lines 33, 35, 946, 1008–1019)
- Delete: `xbridge_mcp/key_validator.py`
- Delete: `tests/test_key_validator.py`

- [ ] **Step 1: Baseline — record the starting state**

Run: `pytest tests/ -q`
Expected: `154 passed, 3 skipped, 1 failed`. The ONE expected failure is
`tests/test_webhooks.py::test_subscription_created_is_idempotent_on_retry`, an
unfinished test (`raise NotImplementedError`) in a file that Task 2 deletes. This
is the known baseline — do NOT try to fix it. Any *other* failure is a real problem;
stop and report it.

- [ ] **Step 2: Remove the validator import in `server.py`**

Delete this line (line 33):
```python
from .key_validator import validate as _validate_key
```

- [ ] **Step 3: Remove the `_XBRIDGE_KEY` env read in `server.py`**

Delete this line (line 35):
```python
_XBRIDGE_KEY = os.environ.get('XBRIDGE_KEY')
```

- [ ] **Step 4: Remove the auth guard at the top of `call_tool`**

In `xbridge_mcp/server.py`, the `call_tool` function currently begins:
```python
@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> CallToolResult:
    """Handle tool invocations."""
    try:
        auth = await _validate_key(_XBRIDGE_KEY)
        if not auth.get('valid'):
            return CallToolResult(
                content=[TextContent(type="text", text="❌ Invalid XBRIDGE_KEY. Get one at xbridgemcp.com")],
                isError=True,
            )
        if auth.get('calls_remaining') == 0:
            return CallToolResult(
                content=[TextContent(type="text",
                    text="⚠️ Daily limit reached (50 calls/day). Upgrade at xbridgemcp.com/pro")],
                isError=True,
            )
        # Original tools
        if name == "grok-chat":
            return await handle_grok_chat(arguments)
```

Replace it with (delete the entire `auth` block so the `try:` flows straight into the dispatcher):
```python
@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> CallToolResult:
    """Handle tool invocations."""
    try:
        # Original tools
        if name == "grok-chat":
            return await handle_grok_chat(arguments)
```

- [ ] **Step 5: Drop the "paid tier" qualifier in the docs-tools comment**

At line ~946, change:
```python
        # xAI Docs tools (xBridge paid tier)
```
to:
```python
        # xAI Docs tools
```

- [ ] **Step 6: Delete the validator module and its test**

Run:
```bash
git rm xbridge_mcp/key_validator.py tests/test_key_validator.py
```

- [ ] **Step 7: Verify the server still imports cleanly**

Run: `python -c "import xbridge_mcp.server"`
Expected: no output, exit 0 (no `ImportError`).

- [ ] **Step 8: Verify no validator references remain in the package**

Run: `grep -rn "key_validator\|_validate_key\|_XBRIDGE_KEY\|XBRIDGE_KEY" xbridge_mcp/`
Expected: no matches (empty output).

- [ ] **Step 9: Run the full suite**

Run: `pytest tests/ -q`
Expected: same as baseline minus the deleted `test_key_validator.py` — i.e. the only
failure is still the known `test_webhooks.py::test_subscription_created_is_idempotent_on_retry`
(removed in Task 2). No NEW failures. (`test_validate_key.py` and `test_webhooks.py`
still collect here — they test `aws/`, which is still present.)

- [ ] **Step 10: Commit**

```bash
git add xbridge_mcp/server.py
git commit -m "feat!: remove XBRIDGE_KEY billing guard and validator

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 2: Delete the AWS billing backend

Removes the entire SAM stack and the two tests that depend on it, together, so collection never breaks.

**Files:**
- Delete: `aws/` (entire tree — Lambdas, `template.yaml`, `samconfig.toml`, `src/`, etc.)
- Delete: `tests/test_validate_key.py`
- Delete: `tests/test_webhooks.py`

- [ ] **Step 1: Confirm these tests import from `aws/`**

Run: `grep -n "aws" tests/test_validate_key.py tests/test_webhooks.py`
Expected: matches showing `from aws...` / `aws.src...` imports — confirms they must be deleted alongside `aws/`.

- [ ] **Step 2: Delete the AWS tree and its tests**

Run:
```bash
git rm -r aws tests/test_validate_key.py tests/test_webhooks.py
```

- [ ] **Step 3: Verify no AWS / billing-backend references remain in source or tests**

Run: `grep -rn "boto3\|dynamodb\|lemonsqueez\|execute-api\|VALIDATE_URL" xbridge_mcp/ tests/`
Expected: no matches (empty output).

- [ ] **Step 4: Run the full suite**

Run: `pytest tests/ -q`
Expected: all tests PASS. Remaining test files: `test_core`, `test_docs_tools`, `test_image_tools`, `test_image_integration`, `test_session_manager`, `test_tool_chains`.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat!: delete AWS SAM billing backend (Lambda/DynamoDB/SES/LS)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 3: Update config and docs to BYOK / v3.0.0

Strips `XBRIDGE_KEY`/tier language from config and docs and bumps the version everywhere.

**Files:**
- Modify: `.env.example`
- Modify: `pyproject.toml` (version line)
- Modify: `README.md` (pricing table ~line 18, config example ~line 62, env table ~line 111)
- Modify: `CLAUDE.md` (tagline line 3, description line 8, version header)

- [ ] **Step 1: Rewrite `.env.example`**

Replace the entire file contents with:
```
# xAI Grok API Configuration — get your key at https://x.ai/api
XAI_API_KEY=

# Optional: force USA routing (e.g. us-east-1)
XAI_REGION=
```

- [ ] **Step 2: Bump the version in `pyproject.toml`**

Change:
```toml
version = "2.1.0"
```
to:
```toml
version = "3.0.0"
```

- [ ] **Step 3: Replace the pricing table in `README.md`**

Find the pricing/tier table (the row at ~line 18 reads `| **Free** | €0/mo | 50 calls/day, all 19 tools, no credit card |`). Replace the entire pricing table (header row, separator, and all tier rows) with:
```markdown
**Free & open source.** Bring your own xAI API key (BYOK) and self-host — all 19 tools, no limits, no account.
```

- [ ] **Step 4: Remove `XBRIDGE_KEY` from the README config example**

At ~line 62, delete the line:
```json
        "XBRIDGE_KEY": "your_xbridge_key_here"
```
If the preceding line (e.g. `"XAI_API_KEY": "your_xai_key_here",`) now has a trailing comma before a closing `}`, remove that trailing comma so the JSON stays valid.

- [ ] **Step 5: Remove the `XBRIDGE_KEY` row from the README env table**

At ~line 111, delete the table row:
```markdown
| `XBRIDGE_KEY` | No | Your xBridge license key (Pro tier). Omit for free tier or self-hosted. |
```

- [ ] **Step 6: Update the `CLAUDE.md` tagline (line 3)**

Change:
```
> Independent MCP server bridging Claude Code → xAI Grok API. BYOK. Paid-first.
```
to:
```
> Independent MCP server bridging Claude Code → xAI Grok API. BYOK. Free & open source.
```

- [ ] **Step 7: Update the `CLAUDE.md` description (line 8)**

In the "What This Is" paragraph, change the final sentence from:
```
Two distributions: free MIT source + paid Docker image (€3.69/mo Pro, BYOK).
```
to:
```
MIT source + Docker image, BYOK.
```

- [ ] **Step 8: Reconcile the `CLAUDE.md` version header to v3.0.0**

In the blockquote header line that reads `> v2.2.0 · Python 3.10+ · ...`, change `v2.2.0` to `v3.0.0`.

- [ ] **Step 9: Verify no key/tier/AWS language survives in docs+config**

Run: `grep -rn "XBRIDGE_KEY\|Paid-first\|paid tier\|Pro tier\|50 calls\|VALIDATE_URL\|execute-api" README.md CLAUDE.md .env.example pyproject.toml`
Expected: no matches (empty output).

- [ ] **Step 10: Commit**

```bash
git add .env.example pyproject.toml README.md CLAUDE.md
git commit -m "docs: drop XBRIDGE_KEY/tier language, bump to v3.0.0

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 4: Final verification sweep

Confirms the end state matches the spec's verification criteria.

**Files:** none (verification only)

- [ ] **Step 1: Full suite green**

Run: `pytest tests/ -q`
Expected: all tests PASS, no collection errors.

- [ ] **Step 2: Server imports clean**

Run: `python -c "import xbridge_mcp.server"`
Expected: exit 0, no output.

- [ ] **Step 3: No validator/key references in the package**

Run: `grep -rn "key_validator\|XBRIDGE_KEY\|_validate_key" xbridge_mcp/`
Expected: no matches.

- [ ] **Step 4: No AWS pointers in runtime/config**

Run: `grep -rn "VALIDATE_URL\|execute-api\|boto3\|dynamodb" xbridge_mcp/ .env.example`
Expected: no matches.

- [ ] **Step 5: Confirm `aws/` is gone from the working tree**

Run: `test ! -e aws && echo "aws/ removed"`
Expected: prints `aws/ removed`.

- [ ] **Step 6: Review the diff summary**

Run: `git log --oneline -4 && git diff --stat HEAD~3`
Expected: three feature/docs commits; stat shows `aws/`, `key_validator.py`, and the three tests deleted, plus `server.py`/docs/config modified.

Do NOT push. Pushing to GitHub requires explicit user confirmation.
