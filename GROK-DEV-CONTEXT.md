# GROK MCP Server - Development Context

> Session memory for the grok-mcp-expert agent. Updated per session.

## Project Overview

**Name**: grok-mcp-server
**Version**: 1.0.0
**Purpose**: MCP Server exposing xAI Grok API as tools for Claude Code
**Stack**: Python 3.10+ | mcp>=1.0.0 | httpx>=0.27.0 | hatchling build

## Architecture

```
grok_mcp_server/
  __init__.py           # Package metadata (v1.0.0)
  server.py             # Main MCP server - tools, handlers, API calls (~1094 lines)
  session_manager.py    # JSON-file-based session persistence (~227 lines)
  tool_chains.py        # Composable chain execution framework (~302 lines)
```

### Key Patterns

- **Single API endpoint**: All requests go through `make_grok_request()` -> `POST https://api.x.ai/v1/responses`
- **Response extraction**: `extract_response_text()` handles nested output structures
- **Tool registration**: `@server.list_tools()` returns Tool list, `@server.call_tool()` dispatches by name
- **Sessions**: File-based JSON in `.grok_sessions/`, singleton `SessionManager`
- **Chains**: `ToolChain` class with `ChainStep` dataclass, `ChainBuilder` for prebuilt patterns
- **Models list**: Hardcoded in `AVAILABLE_MODELS` constant (6 models currently)

### Current MCP Tools (13 total)

| Tool | Handler | Category |
|------|---------|----------|
| grok-chat | handle_grok_chat | Core |
| grok-web-search | handle_grok_web_search | Core |
| grok-x-search | handle_grok_x_search | Core |
| grok-models | handle_grok_models | Core |
| grok-session-create | handle_session_create | Session |
| grok-session-list | handle_session_list | Session |
| grok-session-get | handle_session_get | Session |
| grok-session-delete | handle_session_delete | Session |
| grok-session-chat | handle_session_chat | Session |
| grok-chain-search-summarize | handle_chain_search_summarize | Chain |
| grok-chain-research | handle_chain_research | Chain |
| grok-chain-debug | handle_chain_debug | Chain |

### API Integration

- **Base URL**: `https://api.x.ai/v1/responses` (Responses API format)
- **Auth**: Bearer token via `XAI_API_KEY` env var
- **Timeout**: 300 seconds
- **Client**: httpx.AsyncClient (created per request)

### What's NOT Implemented Yet

1. **Image Generation** - `/v1/images/generations` endpoint not used
2. **Image Editing** - `/v1/images/edits` endpoint not used
3. **Video Generation** - `grok-imagine-video` not integrated
4. **Vision Input** - No image input support in chat tools
5. **Reasoning Models** - `grok-4-1-fast-reasoning` not in model list
6. **Code Execution Tool** - xAI built-in code_execution not exposed
7. **File Analysis Tool** - xAI built-in file_analysis not exposed
8. **Batch API** - 50% discount async processing not available

## Session Log

### 2025-02-12 - Agent Created
- Initial context file created
- Full project audit completed
- xAI API surface mapped against current implementation
- Gap analysis prepared

### 2025-02-12 - Image & Video Generation Plan Completed
- **Deliverable**: `docs/plans/2025-02-12_image_generation_implementation_plan.md`
- **Architecture Decision**: Extend `server.py` (not a separate server) -- same auth, shared httpx client, single MCP registration point
- **API Research Findings**:
  - Image API: `POST /v1/images/generations` + `POST /v1/images/edits` (JSON body, no multipart)
  - Video API: `POST /v1/videos/generations` (async submit) + `GET /v1/videos/{id}` (poll)
  - Image models: `grok-imagine-image` ($0.02), `grok-imagine-image-pro` ($0.07), `grok-2-image-1212` ($0.07)
  - Video model: `grok-imagine-video` ($0.05/sec), supports text-to-video, image-to-video, video editing
  - Response format: `response_format: "b64_json"` for base64, `"url"` for temp URLs
  - Batch: up to 10 images per request
  - Aspect ratios: 14 options including mobile (9:16, 9:19.5) and ultra-wide (20:9)
- **New Tools Designed** (4 total):
  - `grok-image-generate` -- text-to-image with aspect ratio, batch, model selection
  - `grok-image-edit` -- image editing with source URL/base64 input
  - `grok-image-models` -- list all image/video models with pricing
  - `grok-video-generate` -- async video gen with polling (text/image/video input)
- **MCP Image Return Strategy**: Use `ImageContent` type (MCP 2025-11-25 spec) for base64 images, with `TextContent` fallback
- **New Functions**: `make_image_request()`, `make_video_request()`, `_format_image_response()`
- **Updated Models List**: Expanded from 6 to 14 text models + 3 image + 1 video
- **Estimated Code Addition**: ~350 lines to server.py, ~300 lines tests
- **Status**: Plan ready, awaiting main Claude to implement
