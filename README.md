# xBridge MCP

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Docker](https://img.shields.io/badge/docker-nexuswedge%2Fxbridge--mcp-blue)](https://hub.docker.com/r/nexuswedge/xbridge-mcp)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![MCP Registry](https://img.shields.io/badge/MCP-Registry-0ea5e9)](https://registry.modelcontextprotocol.io)

<!-- mcp-name: io.github.hrco/xbridge-mcp -->

**Grok inside Claude Code. Free. Open source. BYOK.**

xBridge MCP is a lightweight, self-hosted MCP server that exposes the full power of **xAI Grok** (including grok-4.20 models) directly inside Claude Code and other MCP clients.

## Why xBridge?

- Full access to Grok-4.20 family (2M context, reasoning, multi-agent)
- 19 tools: chat, web/X search, sessions, chains, image gen/edit, video gen, docs, model listing
- Free and open source — self-host the MIT server with your own key, no limits
- You control your own API key (BYOK)
- No telemetry, no middleman

> **Self-host is free forever.** A managed **Pro** tier (prebuilt Docker image + support) is also available — see [xbridgemcp.com](https://xbridgemcp.com) for pricing.

## Installation

### Docker (Recommended)

```bash
docker pull nexuswedge/xbridge-mcp:latest
docker run -e XAI_API_KEY=your_key nexuswedge/xbridge-mcp:latest
```

### pip

```bash
pip install xbridge-mcp
XAI_API_KEY=your_key xbridge-mcp
```

## Configuration (Claude Code)

Add to your Claude Code config:

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

## Available Tools (19)

| Group | Tools |
|-------|-------|
| Chat | `grok-chat` |
| Search | `grok-web-search`, `grok-x-search` |
| Sessions | `grok-session-create`, `grok-session-chat`, `grok-session-get`, `grok-session-list`, `grok-session-delete` |
| Chains | `grok-chain-search-summarize`, `grok-chain-research`, `grok-chain-debug` |
| Images | `grok-image-generate`, `grok-image-edit`, `grok-image-models` |
| Video | `grok-video-generate` |
| Docs | `grok-docs-list`, `grok-docs-get`, `grok-docs-search` |
| Models | `grok-models` |

## Links

- Product site: https://xbridgemcp.com
- GitHub: https://github.com/hrco/xbridge-mcp
- Docker Hub: https://hub.docker.com/r/nexuswedge/xbridge-mcp
- Release: https://github.com/hrco/xbridge-mcp/releases/tag/v3.0.0

---

*Not affiliated with or endorsed by xAI.*