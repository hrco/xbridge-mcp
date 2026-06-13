# xBridge MCP

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Docker](https://img.shields.io/badge/docker-hrco%2Fxbridge--mcp-blue)](https://hub.docker.com/r/hrco/xbridge-mcp)

Ship Grok-powered MCP workflows in minutes.

xBridge MCP is an MCP server focused exclusively on **xAI Grok API** with 19 tools for chat, web search, X search, sessions, chains, image generation/edit, video generation, and documentation.

> **Independent project. Not affiliated with or endorsed by xAI.**

---

## Philosophy

**Completely free. Open source. BYOK.**

xBridge MCP is a self-hosted MCP server. You run it locally with your own xAI API key. No accounts. No limits. No payments. No telemetry.

**BYOK**: You provide your own `XAI_API_KEY`. xBridge never sees or proxies your key.

### $XBRDG Community Token

[$XBRDG](https://pump.fun/coin/6vUhppYep18WSncUDR6Brt9yZw31ycLDPDEHo13pump) is a community memecoin for supporters. Holding it is purely optional and carries no access privileges or financial promises.

---

## Quick Start (Pro)

```bash
docker pull hrco/xbridge-mcp:latest
docker run -e XAI_API_KEY=your_key_here hrco/xbridge-mcp:latest
```

Or with docker-compose:

```bash
# Set XAI_API_KEY in .env file
docker compose up -d
```

### MCP Client Configuration

```json
{
  "mcpServers": {
    "xbridge": {
      "command": "xbridge-mcp",
      "env": {
        "XAI_API_KEY": "your_xai_key_here"
      }
    }
  }
}
```

---

## Available Tools (19)

### Chat & Models
- `grok-chat`
- `grok-models`

### Search
- `grok-web-search`
- `grok-x-search`

### Session Management
- `grok-session-create`
- `grok-session-list`
- `grok-session-get`
- `grok-session-delete`
- `grok-session-chat`

### Tool Chaining
- `grok-chain-search-summarize`
- `grok-chain-research`
- `grok-chain-debug`

### Image & Video Generation
- `grok-image-generate`
- `grok-image-edit`
- `grok-image-models`
- `grok-video-generate`

### Documentation
- `grok-docs-list`
- `grok-docs-search`
- `grok-docs-get`

---

## Configuration

| Variable | Required | Description |
|---|---|---|
| `XAI_API_KEY` | Yes | Your xAI API key from [x.ai/api](https://x.ai/api) |

## FAQ

### Is xBridge MCP xAI-only?
Yes. xBridge MCP is purpose-built for xAI Grok API.

### Is xBridge MCP affiliated with xAI?
No. It is independent and not endorsed by xAI.

### Who controls API usage and billing?
You do. xBridge uses BYOK (`XAI_API_KEY`).

## License

Commercial license. See [LICENSE](LICENSE).
