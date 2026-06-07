# xBridge MCP

> The only MCP server dedicated exclusively to xAI Grok API. Open source. MIT License. Built with AI, for AI.

## What is xBridge MCP?

xBridge MCP bridges Claude Code to xAI's Grok API via the Model Context Protocol (MCP). It gives your AI agents 19 tools: chat, web search, X/Twitter search, sessions, multi-step research chains, image generation, image editing, and video generation.

**BYOK** — Bring Your Own Key. You use your own xAI API key. xBridge never resells or proxies your API usage.

## Quick Start

```bash
pip install xbridge-mcp
XAI_API_KEY=your_key xbridge-mcp
```

Or with Docker:

```bash
docker pull hrco/xbridge-mcp:latest
docker run -e XAI_API_KEY=your_key hrco/xbridge-mcp:latest
```

## Claude Code Integration

Add to your MCP config:

```json
{
  "mcpServers": {
    "xbridge": {
      "command": "xbridge-mcp",
      "env": {
        "XAI_API_KEY": "your_xai_key",
        "XBRIDGE_KEY": "your_xbridge_key"
      }
    }
  }
}
```

## Tools (19)

```
| Category | Tools |
|----------|-------|
| Chat | grok-chat, grok-models |
| Search | grok-web-search, grok-x-search |
| Sessions | grok-session-create, grok-session-chat, grok-session-list, grok-session-get, grok-session-delete |
| Chains | grok-chain-research, grok-chain-search-summarize, grok-chain-debug |
| Media | grok-image-generate, grok-image-edit, grok-image-models, grok-video-generate |
| Docs | grok-docs-list, grok-docs-search, grok-docs-get |
```

## Links

- [Product Site](https://xbridgemcp.com) — pricing, demos, guide
- [Plain-English Guide](https://xbridgemcp.com/guide.html) — what it is, how to set up
- [$XBRDG Token](https://xbrdg.com) — community loyalty program
- [pump.fun](https://pump.fun/coin/6vUhppYep18WSncUDR6Brt9yZw31ycLDPDEHo13pump)

## Pricing

```
| Tier | Price | Includes |
|------|-------|----------|
| Free | $0 | 50 calls/day, all 19 tools |
| Pro | €9/mo | Unlimited calls, Docker image, priority support |
```

First 50 founders: **€3.69/mo** with code `FOUNDER50`.

---

*Independent project. Not affiliated with xAI. "Grok" is a trademark of xAI.*
