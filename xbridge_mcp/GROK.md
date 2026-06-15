# xbridge_mcp — Grok Instructions

This directory contains the xBridge MCP server (Python).

**When working here as Grok:**
- Read parent GROK/CLAUDE.md first for full context.
- Focus on MCP tools, async Python, xAI API integration.
- Never hardcode XAI_API_KEY.
- Use the test suite with mocked httpx.
- Commit style: feat/fix/chore as in parent.

Run: XAI_API_KEY=... python server.py

See server.py for tool handlers.