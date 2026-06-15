# xBridge MCP

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Docker](https://img.shields.io/badge/docker-hrco%2Fxbridge--mcp-blue)](https://hub.docker.com/r/hrco/xbridge-mcp)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Grok inside Claude Code. Free. Open source. BYOK.**

xBridge MCP is a lightweight, self-hosted MCP server that exposes the full power of **xAI Grok** (including grok-4.20 models) directly inside Claude Code and other MCP clients.

## Why xBridge?

- Full access to Grok-4.20 family (2M context, reasoning, multi-agent)
- 20 tools: chat, web search, X search, image gen/edit, video gen, chains, sessions
- Completely free and open source
- You control your own API key (BYOK)
- No telemetry, no limits, no middleman

## Installation

### Docker (Recommended)

```bash
docker pull hrco/xbridge-mcp:latest
docker run -e XAI_API_KEY=your_key hrco/xbridge-mcp:latest
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

## Available Tools (20)

Full list available in the [documentation](docs/).

## Links

- GitHub: https://github.com/hrco/xbridge-mcp
- Docker Hub: https://hub.docker.com/r/hrco/xbridge-mcp
- Release: https://github.com/hrco/xbridge-mcp/releases/tag/v3.0.0

---

*Not affiliated with or endorsed by xAI.*