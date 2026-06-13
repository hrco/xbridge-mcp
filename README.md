# xBridge MCP

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Docker](https://img.shields.io/badge/docker-hrco%2Fxbridge--mcp-blue)](https://hub.docker.com/r/hrco/xbridge-mcp)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Grok inside Claude Code. Free. Open source. BYOK.**

xBridge MCP is a lightweight, self-hosted MCP server that exposes the full power of **xAI Grok** (including grok-4.20 models) directly inside Claude Code and other MCP clients.

## Why xBridge?

- Full access to Grok-4.20 family (2M context, reasoning, multi-agent)
- 19+ tools: chat, web search, X search, image gen/edit, video gen, chains, sessions
- Completely free and open source
- You control your own API key (BYOK)
- No telemetry, no limits, no middleman

## Quick Start

### Docker (Recommended)

```bash
docker pull hrco/xbridge-mcp:latest
docker run -e XAI_API_KEY=your_key docker run hrco/xbridge-mcp:latest
```

### Python

```bash
pip install xbridge-mcp
XAI_API_KEY=your_key xbridge-mcp
```

## Available Tools

- `grok-chat`
- `grok-web-search`
- `grok-x-search`
- `grok-image-generate`
- `grok-image-edit`
- `grok-video-generate`
- `grok-list-models`
- + 12 more tools

Full list and documentation: see [docs](docs/)

## Philosophy

**Free. Open. Yours.**

xBridge MCP exists to give developers and power users unrestricted access to Grok through the tools they already use.

## Links

- Docker Hub: https://hub.docker.com/r/hrco/xbridge-mcp
- GitHub: https://github.com/hrco/xbridge-mcp

---

*Not affiliated with or endorsed by xAI.*