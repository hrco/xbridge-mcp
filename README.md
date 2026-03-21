# xBridge MCP

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Docker](https://img.shields.io/badge/docker-hrco%2Fxbridge--mcp-blue)](https://hub.docker.com/r/hrco/xbridge-mcp)

Ship Grok-powered MCP workflows in minutes.

xBridge MCP (alias: **conneXt MCP**) is an MCP server focused exclusively on **xAI Grok API** with tools for chat, web search, X search, sessions, chains, image generation/edit, and video generation.

> **Independent project. Not affiliated with or endorsed by xAI.**

---

## Pricing

| Tier | Price | Includes |
|------|-------|----------|
| **Free** | €0/mo | 50 calls/day, all 16 tools, no credit card |
| **Pro** | €9/mo | Unlimited calls, Docker image, priority support |

**Launch special:** First 50 founders pay €3.69/mo with code `FOUNDER50` — [Get Pro](https://xbridgemcp.lemonsqueezy.com/checkout/buy/9e5b9065-0460-4bc5-82d4-de4e8fd69c83)

**BYOK**: You provide your own `XAI_API_KEY`. xBridge never resells xAI API usage.

### $XBRDG Loyalty Program

Hold [$XBRDG](https://pump.fun/coin/6vUhppYep18WSncUDR6Brt9yZw31ycLDPDEHo13pump) for enhanced access:

| Balance | Perk |
|---------|------|
| ≥ 1,000 | 20% off Pro (stacks with FOUNDER50) |
| ≥ 5,000 | 100 calls/day on free tier |
| ≥ 10,000 | Early access to new tools |

> $XBRDG provides access perks for xBridge MCP users. It is not an investment and carries no financial guarantees.

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
        "XAI_API_KEY": "your_xai_key_here",
        "XBRIDGE_KEY": "your_xbridge_key_here"
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
