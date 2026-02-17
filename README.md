# xBridge MCP

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Docker](https://img.shields.io/badge/docker-hrco%2Fxbridge--mcp-blue)](https://hub.docker.com/r/hrco/xbridge-mcp)

Ship Grok-powered MCP workflows in minutes.

xBridge MCP (alias: **conneXt MCP**) is an MCP server focused exclusively on **xAI Grok API** with tools for chat, web search, X search, sessions, chains, image generation/edit, and video generation.

> **Independent project. Not affiliated with or endorsed by xAI.**

---

## Paid-First Access

xBridge MCP is currently available as a paid early-access product.

### Pro — €3.69/month
- xAI-only MCP runtime
- Prebuilt Docker image
- Guided setup docs
- Priority support
- Early-access updates

**BYOK**: You provide your own `XAI_API_KEY`. xBridge never resells xAI API usage.

### Join Early Access
- Checkout: `https://YOUR-CHECKOUT-LINK`
- Onboarding delivery: private setup guide + support channel invite

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
        "XAI_API_KEY": "your_key_here"
      }
    }
  }
}
```

---

## Available Tools (16)

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
