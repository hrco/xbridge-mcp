# xBridge MCP (alias: conneXt MCP)

> Independent MCP server bridging Claude Code → xAI Grok API. BYOK. Free & open source.
> v3.0.0 · Python 3.10+ · 19+ tools · `hrco/xbridge-mcp` on Docker Hub

## What This Is

Python MCP server exposing xAI Grok API as 19+ tools: chat, web search, X search, sessions, chains, image gen, image edit, video gen, docs, and model listing. Supports grok-4.20 family (2M context, reasoning, multi-agent). MIT source + Docker image, BYOK.

## Stack

| Thing | Choice |
|-------|--------|
| Language | Python 3.10+ |
| MCP | `mcp>=1.0.0` |
| HTTP | `httpx>=0.27.0` (async) |
| Build | `hatchling` |
| Entry point | `xbridge-mcp = xbridge_mcp.server:run` |
| Docker | `hrco/xbridge-mcp:latest` |

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
.claude/agents/       # 9 XBRIDGE-* subagents (see Agent Delegation)
```

### Key Patterns

- All xAI API calls go through `make_grok_request()` in `server.py`
- Tools registered via `@server.list_tools()` / `@server.call_tool()`
- Sessions stored as JSON in `.grok_sessions/` — excluded from git
- Response parsing: `extract_response_text()` handles nested output
- MCP tool names keep `grok-*` prefix (API surface, not brand)
- **Async everywhere** — httpx async client, pytest asyncio_mode=auto

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

- **VPS:** `168.231.109.225` (Hostinger Ubuntu, nginx, SSL via certbot)
- **Deploy:** `bash scripts/deploy.sh 168.231.109.225`
- **Sites:** `https://xbridgemcp.com` (product) · `https://xbrdg.com` (token)
- **Document roots:** `/var/www/xbridgemcp.com/html/` · `/var/www/xbrdg.com/html/`

## $XBRDG Token

Community memecoin for xBridge recognition. Solana, pump.fun fair launch, no utility promises.

- **CA:** `6vUhppYep18WSncUDR6Brt9yZw31ycLDPDEHo13pump`
- **pump.fun:** `https://pump.fun/coin/6vUhppYep18WSncUDR6Brt9yZw31ycLDPDEHo13pump`
- **Landing page:** `xbrdg-site/index.html` — pure HTML/CSS/JS, DexScreener embed live
- **Launch assets:** `site/launch-copy.md` · `site/community-playbook.md`

## Key Patterns

### When writing new tools
1. Add handler function in `server.py` → `handle_grok_<name>(arguments)`
2. Add `Tool(...)` entry in `list_tools()` with proper `inputSchema`
3. Add test in `tests/` using mocked httpx — never hit real API
4. All API calls go through `make_grok_request()` — never direct httpx

### When modifying model support
- `AVAILABLE_MODELS` list in `server.py` is the single source of truth
- Model enum in tool schemas auto-generates from `AVAILABLE_MODELS`
- Regional endpoint respects `XAI_REGION` env var across all base URLs

### Forbidden Patterns
- Never hardcode API keys in any file
- Never use synchronous HTTP (always httpx async)
- Never skip the `make_grok_request()` abstraction
- Never use `requests` library

## Agent Delegation

13 agents in `.claude/agents/` — all tracked in git:

### Engineering Agents
| Agent | Domain |
|-------|--------|
| `xbridge-lead-coder` | Code quality, optimization, refactoring existing code |
| `xbridge-backend-dev` | New feature development, new MCP tools, xAI API integrations |
| `xbridge-python-specialist` | Async correctness, concurrency, httpx lifecycle, stdio safety, types, test architecture |
| `xbridge-mcp-specialist` | MCP protocol, tool schemas, inputSchema design, Claude Code integration |
| `xbridge-frontend-dev` | xbridgemcp.com product site |

**Engineering agent handoff model:**
1. `xbridge-backend-dev` implements → 2. `xbridge-python-specialist` validates runtime correctness → 3. `xbridge-mcp-specialist` validates schema/protocol → 4. `xbridge-lead-coder` reviews quality

### Launch / $XBRDG Agents
| Agent | Domain |
|-------|--------|
| `XBRIDGE-STRATEGY-LEAD` | Master launch coordinator |
| `XBRIDGE-FRONTEND-DEV` | Token landing page (xbrdg.com) |
| `XBRIDGE-ONCHAIN-OPS` | Solana/pump.fun deployment |
| `XBRIDGE-BRANDING-GURU` | Logo, visuals (grok-image-generate) |
| `XBRIDGE-CONTENT-CREATOR` | Tweets, memes, copy |
| `XBRIDGE-MARKETING-STRATEGIST` | X/Twitter, viral tactics |
| `XBRIDGE-COMMUNITY-MANAGER` | Telegram/Discord |
| `XBRIDGE-ANALYTICS-TRACKER` | On-chain metrics, sentiment |
| `XBRIDGE-GITHUB-CLEANUP` | Repo hygiene, secrets audit |
| `xbridge-github-expert` | Public launch prep — file audit, .gitignore, README/CONTRIBUTING/CHANGELOG, secret scan |

## Private Vault

Sensitive launch assets, metrics, copy templates:
```
~/mylab/_xbridge_private_vault/20260217-084313/
```
Never commit vault contents. Never reference vault paths in code.

## Code Style

- Use comments sparingly. Only comment complex code.

## Commit Style

```
feat: add grok-video-generate tool
fix: handle image API timeout
chore: update deploy script
```
