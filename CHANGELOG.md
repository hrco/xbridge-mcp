# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.1.0] - 2026-03-21

### Added
- $XBRDG loyalty program (tiered perks for token holders)
- Unified pricing section: Free (50 calls/day) + Pro (€9/mo)
- FOUNDER50 launch special (€3.69/mo for first 50 founders)
- Free key signup via AWS Lambda + SES email delivery
- LemonSqueezy checkout integration for Pro tier
- FAQ entries for pricing and $XBRDG

### Changed
- Pricing model: €9/mo real price (was €3.69 flat)
- Site redesigned with two-tier pricing grid

## [2.0.0] - 2026-03-01

### Added
- Image generation tool (`grok-image-generate`)
- Image editing tool (`grok-image-edit`)
- Image model listing (`grok-image-models`)
- Video generation tool (`grok-video-generate`)
- Documentation tools (`grok-docs-list`, `grok-docs-search`, `grok-docs-get`)
- Tool chaining: search-summarize, research, debug chains
- Session management: create, list, get, delete, chat
- Key validation middleware (`XBRIDGE_KEY` env var)
- Docker distribution (`hrco/xbridge-mcp`)
- Product site (xbridgemcp.com) and token site (xbrdg.com)
- AWS Lambda backend for freemium key management

### Changed
- Renamed from "Grok MCP Server" to "xBridge MCP"
- Tool count: 16 → 19 (added 3 docs tools)
- Architecture: single `server.py` with `session_manager.py` and `tool_chains.py`

### Infrastructure
- httpx async client (singleton pattern)
- pytest-asyncio test suite with mocked httpx
- SAM template for AWS Lambda deployment

## [1.0.0] - 2025-01-04

### Added
- Initial release of xBridge MCP
- Chat completions with Grok models
- Web search with domain filtering
- X/Twitter search with handle filtering and date ranges
- Session management for persistent conversation history
- Tool chaining for multi-step workflows
- Commercial licensing framework

### Infrastructure
- Python 3.10+ support
- MCP protocol integration
- Persistent session storage
- Async/await architecture
