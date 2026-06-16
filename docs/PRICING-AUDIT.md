# Pricing Audit — 2026-06-16

## New Pricing (target)
- Free: €0 (50 calls/day)
- Pro: €4/mo (€2/mo Founder — first 50, lifetime lock)
- Team: €12/mo (5 seats, planned)

## Old Pricing (to be replaced)
- Pro: €9/mo (regular)
- Founder: €3.69/mo with code `FOUNDER50` (59% off)
- XBRDG stacking: 20% off Pro

---

## Files needing changes

### 1. site/guide.html — Has FULL old pricing (critical)
- Line 152: `$0` (dollar sign — should be `€0`)
- Line 153: `€9/mo` → should be `€4/mo`
- Line 155: `€3.69/mo` with `FOUNDER50` → should be `€2/mo` with `FOUNDER50`
- Line 165: `20% off Pro (stacks with FOUNDER50)` — needs updated stacking amount

### 2. docs/wiki/Home.md — Has FULL old pricing (critical)
- Line 68: `$0` (dollar sign — should be `€0`)
- Line 69: `€9/mo` → should be `€4/mo`
- Line 72: `€3.69/mo` with `FOUNDER50` → should be `€2/mo` with `FOUNDER50`

### 3. docs/wiki/XBRDG-Loyalty.md — Has FULL old pricing + stale stacking math (critical)
- Line 30: `Pro: €9/mo` → should be `€4/mo`
- Line 31: `stacks with FOUNDER50` — no explicit price, but implied old
- Line 50: `Base Pro price: €9.00/mo` → should be `€4.00/mo`
- Line 51: `FOUNDER50 code: €3.69/mo (59% off)` → should be `€2.00/mo (50% off)`
- Line 52: `+ $XBRDG 20% off: €2.95/mo` → should be `€1.60/mo`

### 4. docs/wiki/Setup.md — References XBRIDGE_KEY (already removed from code)
- Line 8: References `xbridgemcp.com/#pricing` for getting a key — needs update
- Line 21: `export XBRIDGE_KEY=your_xbridge_key # optional`
- Line 29: `-e XBRIDGE_KEY=your_xbridge_key` in docker run example
- Line 36: `XBRIDGE_KEY=your_xbridge_key` in .env example
- Line 65: `"XBRIDGE_KEY": "your_xbridge_key"` in MCP config JSON
- Line 82: `XBRIDGE_KEY` row in env var table
- Line 110: Link to product site for pricing

### 5. site/app.js — Dead AWS API Gateway URL (critical backend dependency)
- Line 3: `const API_BASE = 'https://y0xx9n1oz7.execute-api.eu-west-1.amazonaws.com';`
  This AWS endpoint is DEAD — the entire AWS SAM stack has been deleted (see `docs/superpowers/plans/2026-06-07-de-aws-billing-excision.md`).
  All `fetch()` calls to this URL in the same file will fail silently:
  - Line 171: `fetch(\`${API_BASE}/keys/free\`, ...)` — Free key form submission (dead)
  - Line 198: `fetch(\`${API_BASE}/keys/resend\`, ...)` — Key resend (dead)
  - Line 222: `fetch(\`${API_BASE}/keys/verify-xbrdg\`, ...)` — XBRDG wallet verification (dead)
  The free key form and XBRDG loyalty form on the product site are non-functional.

### 6. .claude/settings.local.json — Dead AWS API URL in allowed Bash command
- Line 10: `"Bash(BASE=\"https://y0xx9n1oz7.execute-api.eu-west-1.amazonaws.com\")"`
  This whitelists the dead AWS URL in the allowed Bash commands.

### 7. site/assets/tweet-thread.md — Has OLD pricing (low priority, historical copy)
- Line 17: `€3.69/mo · BYOK · Docker.` → should be `€2/mo`
- Line 73: `16 tools · €3.69/mo` → should be `€2/mo` (also says 16 tools, now 19+)

### 8. xbrdg-site/index.html — References FOUNDER50 but pricing is ALREADY new (minor)
- Line 515: `20% off Pro (stacks with FOUNDER50: €1.60/mo)` — The €1.60 is correct under new pricing (20% off €2), but the FOUNDER50 reference is to the old code name.

---

## Inconsistencies found

### $ vs € currency mismatch
- **site/index.html** Line 170: Uses `€0` (euro — **correct**)
- **site/guide.html** Line 152: Uses `$0` (dollar — **inconsistent** with index.html)
- **docs/wiki/Home.md** Line 68: Uses `$0` (dollar — **inconsistent**)
- These should uniformly use `€` since all other pricing is in euros.

### Dead AWS API Gateway URL
- **site/app.js:3** — `https://y0xx9n1oz7.execute-api.eu-west-1.amazonaws.com`
- **.claude/settings.local.json:10** — same URL in allowed Bash command
- The entire AWS SAM backend has been deleted per `docs/superpowers/plans/2026-06-07-de-aws-billing-excision.md`. All site forms (`/keys/free`, `/keys/resend`, `/keys/verify-xbrdg`) are dead endpoints.

### NEW pricing in site/index.html vs OLD pricing in site/guide.html
- `index.html` uses **new** pricing (€0, €2/€4, FOUNDER50 badge, team planned)
- `guide.html` uses **old** pricing (€9, €3.69, FOUNDER50 code)
- These two HTML files are inconsistent with each other. `guide.html` was missed when `index.html` was updated.

### XBRDG stacking math inconsistency
- **docs/wiki/XBRDG-Loyalty.md:50-52** has old stacking: `€9 → €3.69 → €2.95`
- **xbrdg-site/index.html:515** has new stacking result: `€1.60/mo`
- The wiki doc needs the full stacking chain recalculated for new pricing.

### FOUNDER50 vs new pricing structure
- The new pricing keeps the "first 50 founders get discounted Pro" concept
- But the old code `FOUNDER50` gave 59% off (€9→€3.69)
- New pricing is 50% off (€4→€2)
- Current `site/index.html` uses the **new** prices with the **old** badge text `FOUNDER50`
- This is a naming inconsistency — the badge and all references still say `FOUNDER50` even though the discount math has changed

### XBRIDGE_KEY references still in docs/wiki
- **docs/wiki/Setup.md** — full XBRIDGE_KEY env var references (6 lines)
- **docs/wiki/Home.md** — XBRIDGE_KEY in JSON config example (line 36)
- These were not cleaned up when `XBRIDGE_KEY` was removed from the codebase (v3.0.0)

### Old site/index.html references to pricing anchor
- **site/usage-examples.html** Lines 28, 30, 41, 42 — link to `./index.html#pricing` (anchor still valid)

---

## Files that are ALREADY correct (no changes needed)

| File | Why it's OK |
|------|-------------|
| `site/index.html` | NEW pricing: €0 Free, €2/€4 Pro, FOUNDER50 badge with correct amounts. XBRDG stacking at €1.60 is correct. |
| `CLAUDE.md` | No pricing data. Uses "BYOK. Free & open source." tagline (correct). |
| `README.md` | No pricing table. Clean MCP config (no XBRIDGE_KEY). BYOK only. |
| `CHANGELOG.md` | No pricing data. |
| `CONTRIBUTING.md` | No pricing data. |
| `SECURITY.md` | No pricing data. |
| `STANDARDS.md` | No pricing data. |
| `.env.example` | Clean — only XAI_API_KEY and XAI_REGION. No XBRIDGE_KEY. |
| `.workflow-prompt.md` | No pricing data. |
| `.agent-context.md` | No pricing data. |
| `docs/xbridge-mcp-config.example.json` | Clean — only XAI_API_KEY. No XBRIDGE_KEY. |
| `docs/wiki/Tools-Reference.md` | No pricing data. |
| `docs/wiki/_Sidebar.md` | No pricing data. |
| `xbridge_mcp/server.py` | Already cleaned: no `paid tier` comment, no XBRIDGE_KEY import, no auth guard. (Was cleaned in v3.0.0 excision.) |
| `xbrdg-site/GROK.md` | No pricing data. |
| `xbridge_mcp/GROK.md` | No pricing data. |
| All files under `site/assets/branding/` | Images, no text pricing. |
| All files under `tests/` | Test code references $0.02, $0.07 for xAI image API costs (not xBridge pricing — those are xAI's own prices, correct). |
| All files under `posts/` | Historical X posts, not current product docs. $XBRDG MC references are market data. |
| All files under `scripts/` | Deployment/infrastructure, no pricing. |
| `site/usage-examples.html` | No pricing content, only nav links to `#pricing` anchor (valid). |
| `site/styles.css` | CSS classes only (`.pricing-grid`, `.pricing-card`, etc.) — no text values. |
| `.claude/agent-memory/` | Audit findings only, no pricing data. |
| `.claude/agents/` | **Empty directory** — nothing to check. |

---

## Summary of file counts

| Category | Count |
|----------|-------|
| Files with OLD pricing (€9, €3.69, etc.) | 4 |
| Files with dead AWS API URL | 2 |
| Files with XBRIDGE_KEY references to remove | 2 |
| Files with $ vs € inconsistency | 2 |
| Files already correct | 26+ |
