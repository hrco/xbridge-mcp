# xBridge MCP (alias: conneXt MCP)

> Independent MCP server bridging Claude Code → xAI Grok API. BYOK. Free & open source.
> v3.0.0 · Python 3.10+ · 19+ tools · `hrco/xbridge-mcp` on Docker Hub

## What This Is

Python MCP server exposing xAI Grok API as 19+ tools: chat, web search, X search, sessions, chains, image gen, image edit, video gen, docs, and model listing. Supports grok-4.20 family (2M context, reasoning, multi-agent). MIT source + Docker image, BYOK.

## Stack

| Thing | Choice |
|-------|--------|
| Language | Python 3.10+ (`requires-python = ">=3.10"`) |
| MCP | `mcp>=1.0.0` (unpinned floor) |
| HTTP | `httpx>=0.27.0` (async, unpinned floor) |
| Build | `hatchling` |
| Entry point | `xbridge-mcp = xbridge_mcp.server:run` |
| Docker | `hrco/xbridge-mcp:latest` — base image `python:3.12-slim` |

## Architecture

```
xbridge_mcp/
  server.py           # MCP server + all 19+ tool handlers (~1960 lines)
  session_manager.py  # JSON-file session persistence (.grok_sessions/)
  tool_chains.py      # Chain execution (search→summarize, research, debug)
site/                 # xbridgemcp.com — product site (nginx static)
xbrdg-site/           # xbrdg.com — $XBRDG token landing page (nginx static)
scripts/
  deploy.sh           # rsync both sites to Hostinger VPS
  vps-setup.sh        # fresh Ubuntu VPS bootstrap (nginx + certbot)
tests/                # pytest-asyncio, mock httpx — no real API calls
.claude/agents/       # 4 subagents (live but gitignored — see Agent Delegation)
```

## Quick Start

```bash
pip install -e ".[dev]"
XAI_API_KEY=your_key xbridge-mcp          # stdio mode
XAI_API_KEY=your_key python run_server.py  # alternative
```

## Testing

```bash
pytest tests/ -v                           # all tests
pytest tests/test_image_tools.py -v        # image tools
pytest tests/test_docs_tools.py -v         # docs MCP tools
```

Mock httpx — never hits real API in tests. Add `@pytest.mark.asyncio` not needed (asyncio_mode=auto).

## Docker

```bash
docker build -t hrco/xbridge-mcp:latest .
docker compose up -d                       # uses .env for XAI_API_KEY
docker push hrco/xbridge-mcp:latest
```

**Gotcha:** Never hardcode `XAI_API_KEY` in Dockerfile ENV — inject at runtime only.

## Environment

| Variable | Required | Notes |
|----------|----------|-------|
| `XAI_API_KEY` | Yes | From x.ai/api — never commit |
| `XAI_REGION` | No | Regional endpoint (e.g., `us-east-1`). Forces USA routing. Default: global auto-route |

## grok-4.20 Models (Latest)

| Model | Context | Capabilities |
|-------|---------|-------------|
| `grok-4.20-0309-reasoning` | 2M | Reasoning, function calling, structured output |
| `grok-4.20-0309-non-reasoning` | 2M | Function calling, structured output |
| `grok-4.20-multi-agent-0309` | 2M | Multi-agent orchestration, reasoning |

Regional endpoint: `https://us-east-1.api.x.ai` (set via `XAI_REGION=us-east-1`)

## Deployment

- **VPS:** `76.13.48.186` (Hostinger Ubuntu, nginx, SSL via certbot; SSH user `claude`)
- **Deploy:** `bash scripts/deploy.sh 76.13.48.186` (override user via `VPS_USER=…`)
- **Sites:** `https://xbridgemcp.com` (product) · `https://xbrdg.com` (token)
- **Document roots:** `/var/www/xbridgemcp.com/html/` · `/var/www/xbrdg.com/html/`

### CI/CD (GitHub Actions)

- **`.github/workflows/docker.yml`** — builds + pushes `hrco/xbridge-mcp` to Docker Hub on push to `main` and `v*` tags. Needs repo secrets `DOCKERHUB_USERNAME` (= `hrco`) and `DOCKERHUB_TOKEN` (**Read/Write/Delete** access token). If push 403s with `insufficient_scope`, the token is read-only — regenerate it with write scope.
- **`.github/workflows/publish-mcp.yml`** — publishes `server.json` to the MCP Registry on `v*` tags via `mcp-publisher` (GitHub OIDC, no secret).
- Both workflows are tracked: `.gitignore` ignores `.github/*` but un-ignores `.github/workflows/` (Actions only run if committed to GitHub). Workflow files carry no secrets.
- Actions are pinned to Node-24 releases (checkout@v5, docker/* v4/v7) — Node 20 is deprecated on runners.

## $XBRDG Token

Community memecoin (Solana, pump.fun fair launch, no utility promises).
CA `6vUhppYep18WSncUDR6Brt9yZw31ycLDPDEHo13pump` (pump.fun: `/coin/<CA>`).
Landing `xbrdg-site/`; launch copy/playbook in `site/launch-copy.md`, `site/community-playbook.md`.

## Key Patterns

**Conventions**
- All xAI API calls go through `make_grok_request()` in `server.py` — never direct httpx, never `requests`.
- **Async everywhere** (httpx async client; pytest `asyncio_mode=auto`).
- Tools registered via `@server.list_tools()` / `@server.call_tool()`; MCP tool names keep the `grok-*` prefix (API surface, not brand).
- Sessions persist as JSON in `.grok_sessions/` (git-excluded). Response parsing: `extract_response_text()` handles nested output.

**When writing a new tool**
1. Add `handle_grok_<name>(arguments)` in `server.py`
2. Add a `Tool(...)` entry in `list_tools()` with a proper `inputSchema`
3. Add a test in `tests/` using mocked httpx — never hit the real API

**When modifying model support**
- `AVAILABLE_MODELS` in `server.py` is the single source of truth; tool-schema enums auto-generate from it.
- Regional endpoint respects `XAI_REGION` across all base URLs.

**Forbidden:** hardcoding API keys · synchronous HTTP · skipping `make_grok_request()` · using `requests`.

## Agent Delegation

4 agents in `.claude/agents/` — **live subagents, but gitignored** (loaded by Claude Code, not published to the public OSS repo). `.gitignore` excludes `.claude/agents/`. Consolidated 2026-06-22 from 15 → 4 for a lean, non-overlapping roster.

| Agent | Domain |
|-------|--------|
| `xbridge-engineer` | All Python code: new MCP tools, refactoring/optimization, runtime correctness (async/httpx/stdio/types), tests, packaging, Docker, CI, releases, repo/secret hygiene |
| `xbridge-mcp-specialist` | MCP protocol contract: tool schemas, inputSchema design, naming, client compatibility, transport/discovery debugging |
| `xbridge-web-engineer` | Both static sites — xbridgemcp.com (`site/`) and xbrdg.com (`xbrdg-site/`) — and deploys |
| `xbridge-growth` | $XBRDG + product marketing: strategy, content/copy, branding direction, community, on-chain/pump.fun ops, analytics |

**Engineering handoff:** `xbridge-mcp-specialist` designs/validates the tool schema; `xbridge-engineer` builds the handler and validates runtime correctness. The specialist is called before implementation (schema design) and after (compliance check).

## Private Vault

Sensitive launch assets, metrics, copy templates:
```
~/mylab/_xbridge_private_vault/20260217-084313/
```
Never commit vault contents. Never reference vault paths in code.

## Code & commits

Comment discipline (sparingly, only complex code) and conventional-commit prefixes
(`feat:` / `fix:` / `chore:`) follow global `~/.claude/CLAUDE.md`.
