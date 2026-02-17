# xBridge MCP

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Docker](https://img.shields.io/badge/docker-hrco%2Fxbridge--mcp-blue)](https://hub.docker.com/r/hrco/xbridge-mcp)

Ship Grok-powered MCP workflows in minutes.

xBridge MCP (alias: **conneXt MCP**) is an MCP server wrapping xAI's Grok API with 16 tools for chat, web search, X/Twitter search, sessions, chains, image generation/edit, and video generation.

> **xBridge MCP is an independent project. Not affiliated with or endorsed by xAI.**
>
> Internal package/runtime names currently remain `xbridge_*` for compatibility.

## Why xBridge

- **BYOK control** with your own `XAI_API_KEY`
- **Developer-first** MCP tool surface for coding workflows
- **Fast path to production** via prebuilt Docker image (Pro)
- **Open source core** (MIT) + optional low-cost Pro support

---

## Pricing

| | Free (GitHub) | Pro (€3.69/mo) |
|---|---|---|
| All 16 MCP tools | Yes | Yes |
| Source code (MIT) | Yes | Yes |
| Install method | `pip install` from source | Pre-built Docker image |
| Docker Hub image | -- | `hrco/xbridge-mcp:latest` |
| Auto-updates | Manual | Docker tags |
| Support | GitHub Issues | Priority |
| New tool early access | -- | Yes |

**BYOK**: You always bring your own `XAI_API_KEY`. We never touch your API key.

### Buy Pro

- Checkout link (LemonSqueezy/Stripe): `https://YOUR-CHECKOUT-LINK`
- Subscription price: **€3.69/month**
- Delivery: Private onboarding + Pro install guide + priority support

---

## Quick Start

### Free (from source)

```bash
git clone https://github.com/hrco/xbridge-mcp.git
cd xbridge-mcp
pip install -e .
export XAI_API_KEY=REDACTED
xbridge-mcp
```

### Pro (Docker)

```bash
docker pull hrco/xbridge-mcp:latest
docker run -e XAI_API_KEY=REDACTED
```

Or with docker-compose:

```bash
# Set XAI_API_KEY in .env file
docker compose up -d
```

### MCP Client Configuration

Add to your MCP client config (e.g. Claude Desktop, `.mcp.json`):

```json
{
  "mcpServers": {
    "xbridge": {
      "command": "xbridge-mcp",
      "env": {
        "XAI_API_KEY": "your_key_here"
      }
    }
  }
}
```

---

## Available Tools (16)

### Chat & Models
| Tool | Description |
|------|-------------|
| `grok-chat` | Chat with Grok models (grok-4, grok-4-1-fast, etc.) |
| `grok-models` | List available text models with pricing |

### Search
| Tool | Description |
|------|-------------|
| `grok-web-search` | Web search with domain filtering + image understanding |
| `grok-x-search` | X/Twitter search with handle/date filtering + media understanding |

### Session Management
| Tool | Description |
|------|-------------|
| `grok-session-create` | Create persistent conversation session |
| `grok-session-list` | List active sessions |
| `grok-session-get` | Get session details + history |
| `grok-session-delete` | Delete a session |
| `grok-session-chat` | Chat within session context (auto-maintains history) |

### Tool Chaining
| Tool | Description |
|------|-------------|
| `grok-chain-search-summarize` | Search + summarize in one call |
| `grok-chain-research` | Multi-source research (web + X) with synthesis |
| `grok-chain-debug` | Debug workflow (search X for issues + generate fix) |

### Image & Video Generation
| Tool | Description |
|------|-------------|
| `grok-image-generate` | Text-to-image generation (multiple models, batch support) |
| `grok-image-edit` | Edit images with natural language instructions |
| `grok-image-models` | List image/video models with pricing |
| `grok-video-generate` | Text/image-to-video generation (async with polling) |

---

## Architecture

```
xbridge-mcp/
├── xbridge_mcp/
│   ├── __init__.py
│   ├── server.py           # MCP server + all 16 tool handlers
│   ├── session_manager.py  # JSON-file session persistence
│   └── tool_chains.py      # Composable chain workflows
├── tests/
├── pyproject.toml
├── Dockerfile
├── docker-compose.yml
└── run_server.py
```

Sessions are stored in `.grok_sessions/` as JSON files.

## Configuration

| Variable | Required | Description |
|----------|----------|-------------|
| `XAI_API_KEY` | Yes | Your xAI API key from [x.ai/api](https://x.ai/api) |

## FAQ

### Is xBridge MCP affiliated with xAI?
No. xBridge MCP is an independent project and is not endorsed by xAI.

### Why pay for Pro if source is free?
Pro is for convenience: prebuilt Docker, guided setup, and priority support.

### Who controls API usage and billing?
You do. xBridge uses BYOK (`XAI_API_KEY`), so your key and costs stay under your control.

### Is xBridge MCP the same as conneXt MCP?
Yes. **xBridge MCP** is the primary brand, while **conneXt MCP** is an alias used in some docs.

## Development

```bash
pip install -e ".[dev]"
pytest
```

## License

MIT License - see [LICENSE](LICENSE).

## Disclaimer

xBridge MCP is an independent, community-driven project. It is **not affiliated with, endorsed by, or sponsored by xAI**. "Grok" is a trademark of xAI. This project uses the xAI API under its published terms of service. Users are responsible for their own API usage and costs.
