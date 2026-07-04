# Setup

> Get xBridge MCP running in 2 minutes. Three options: pip, Docker, or source.

## Prerequisites

- **xAI API Key** — Get one free at [x.ai/api](https://x.ai/api) (xAI gives you free credits to start)
- **Python 3.10+** (for pip install) or **Docker** (for container)

## Option 1: pip install

```bash
pip install xbridge-mcp
```

Run it:

```bash
export XAI_API_KEY=your_xai_key
xbridge-mcp
```

## Option 2: Docker

```bash
docker pull nexuswedge/xbridge-mcp:latest
docker run -e XAI_API_KEY=your_xai_key nexuswedge/xbridge-mcp:latest
```

Or with docker-compose, create a `.env` file:

```
XAI_API_KEY=your_xai_key
```

Then:

```bash
docker compose up -d
```

## Option 3: From Source

```bash
git clone git@github.com:hrco/xbridge-mcp.git
cd xbridge-mcp
pip install -e ".[dev]"
XAI_API_KEY=your_key xbridge-mcp
```

## Connect to Claude Code

Add this to your Claude Code MCP config (`~/.claude/settings.json` or project `.mcp.json`):

```json
{
  "mcpServers": {
    "xbridge": {
      "command": "xbridge-mcp",
      "env": {
        "XAI_API_KEY": "your_xai_key"
      }
    }
  }
}
```

Restart Claude Code. All 19 tools are now available.

**Pro tip:** Claude can do this for you. Just paste the JSON above into your chat and say "add this MCP server" — Claude will find the right config file and set it up.

## Environment Variables

```
| Variable | Required | Description |
|----------|----------|-------------|
| XAI_API_KEY | Yes | Your xAI API key from x.ai/api |
```

## Verify It Works

Once connected to Claude Code, try:

- *"Ask Grok what's trending on X right now"* — tests `grok-x-search`
- *"Use Grok to search the web for MCP servers"* — tests `grok-web-search`
- *"Chat with Grok about Python best practices"* — tests `grok-chat`

If you see responses, you're good.

## Troubleshooting

```
| Problem | Fix |
|---------|-----|
| XAI_API_KEY not set | Export the variable or add it to your .env file |
| Tools not showing in Claude | Restart Claude Code after adding MCP config |
| Connection refused | Make sure xbridge-mcp process is running |
| 401 Unauthorized | Check your xAI API key is valid at x.ai/api |
```

## Next Steps

- [Tools Reference](Tools-Reference) — all 19 tools with parameters and examples
- [$XBRDG Loyalty](XBRDG-Loyalty) — hold $XBRDG for perks
- [Product Site](https://xbridgemcp.com) — pricing and demos
