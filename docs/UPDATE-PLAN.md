# xBridge MCP: Update Plan

Audit date: 2026-07-01
Audit source: [xAI docs](https://docs.x.ai/developers) vs `xbridge_mcp/server.py` (v3.0.0)
Issues: [#18](https://github.com/hrco/xbridge-mcp/issues/18) [#19](https://github.com/hrco/xbridge-mcp/issues/19) [#20](https://github.com/hrco/xbridge-mcp/issues/20) [#21](https://github.com/hrco/xbridge-mcp/issues/21)

---

## P0 — Stale data (ships wrong info to users)

### Step 1: Fix model pricing, context sizes, and add missing models

**Issue:** [#18](https://github.com/hrco/xbridge-mcp/issues/18)
**Files:** `xbridge_mcp/server.py` (L41-71, L1213-1267), `docs/wiki/Tools-Reference.md`
**Estimate:** 15m

Actions:
- Update `handle_grok_models()` pricing/context for grok-4.20 family ($1.25/$2.50, 1M ctx)
- Add `grok-build-0.1` to `AVAILABLE_MODELS`
- Add `grok-imagine-image-quality` to `IMAGE_MODELS`
- Add `grok-imagine-video-1.5` to `VIDEO_MODELS`
- Update `handle_image_models()` to describe new models
- Update Tools-Reference.md model enum

---

## P1 — Missing behavior / broken edge cases

### Step 2: Add `enable_image_search` to grok-web-search

**Issue:** [#19](https://github.com/hrco/xbridge-mcp/issues/19) item 1
**File:** `xbridge_mcp/server.py`
**Estimate:** 10m

Actions:
- Add `enable_image_search` boolean param to `grok-web-search` inputSchema
- Pass it through in `handle_grok_web_search()` payload
- Add test

### Step 3: Fix video generation `failed` status

**Issue:** [#19](https://github.com/hrco/xbridge-mcp/issues/19) item 2
**File:** `xbridge_mcp/server.py` (L342-355)
**Estimate:** 10m

Actions:
- Add `status == "failed"` handling in `make_video_request()` polling loop
- Surface `error.code` and `error.message` from API response
- Add test

### Step 4: Add 1080p + grok-imagine-video-1.5 to video tools

**Issue:** [#19](https://github.com/hrco/xbridge-mcp/issues/19) items 3-4
**File:** `xbridge_mcp/server.py`
**Estimate:** 5m

Actions:
- Add `"1080p"` to `VIDEO_RESOLUTIONS`
- Add `grok-imagine-video-1.5` to `VIDEO_MODELS`
- Update tool descriptions

---

## P2 — New API features (backward-compatible)

### Step 5: Add Priority Processing (`service_tier`) support

**Issue:** [#20](https://github.com/hrco/xbridge-mcp/issues/20) item 1
**File:** `xbridge_mcp/server.py`
**Estimate:** 30m

Actions:
- Add `service_tier` param (enum: `"auto"`, `"priority"`) to tool schemas for: `grok-chat`, `grok-web-search`, `grok-x-search`, `grok-image-generate`, `grok-image-edit`, `grok-video-generate`
- Thread through `make_grok_request()`, `make_image_request()`, `make_video_request()` payloads
- Surface `response.service_tier` in result text
- Add tests

### Step 6: Add Cost Tracking

**Issue:** [#20](https://github.com/hrco/xbridge-mcp/issues/20) item 2
**File:** `xbridge_mcp/server.py`
**Estimate:** 15m

Actions:
- Extract `cost_in_usd_ticks` from `response.usage` in text, image, and video handlers
- Append cost line to result text (e.g. "Cost: $0.0015")

---

## P3 — Whole new tool areas

### Step 7: Text-to-Speech tool

**Issue:** [#21](https://github.com/hrco/xbridge-mcp/issues/21)
**New tool:** `grok-tts`
**Estimate:** 45m

Actions:
- Endpoint: `POST /v1/audio/speech`
- Params: `input` (text), `voice`, `speed`, `response_format`
- Returns audio bytes as base64 or URL
- Follow existing patterns: handler + tool registration + test
- Update docs/wiki + CLAUDE.md tool count

### Step 8: Speech-to-Text tool

**Issue:** [#21](https://github.com/hrco/xbridge-mcp/issues/21)
**New tool:** `grok-stt`
**Estimate:** 45m

Actions:
- Endpoint: `POST /v1/audio/transcriptions`
- Params: file (URL or base64), `language`, `response_format`
- Smart Turn support (`smart_turn`, `smart_turn_timeout`) — May 2026 feature
- Follow existing patterns

### Step 9: Files API tools

**Issue:** [#21](https://github.com/hrco/xbridge-mcp/issues/21)
**New tools:** `grok-file-upload`, `grok-file-list`, `grok-file-delete`, `grok-file-public-url`
**Estimate:** 1h

Actions:
- Basic CRUD wrapping `/v1/files/*`
- Upload from URL or base64
- Public URL creation with optional expiry
- Integrate with Imagine (`image_file_id`, `video_file_id`)

### Step 10: Context Compaction tool

**Issue:** [#21](https://github.com/hrco/xbridge-mcp/issues/21)
**New tool:** `grok-context-compact`
**Estimate:** 30m

Actions:
- Endpoint: `POST /v1/responses/compact`
- Input: existing messages/session
- Output: compacted messages for reuse

---

## Verification

After each step:

```bash
pytest tests/ -v
```

Final smoke test:

```bash
XAI_API_KEY=sk-... python -m xbridge_mcp.server
```

---

## Summary

| Priority | Steps | Total time | Type |
|----------|-------|------------|------|
| P0 | 1 | 15m | Bug fix |
| P1 | 2-4 | 25m | Bug fix / missing params |
| P2 | 5-6 | 45m | Feature addition |
| P3 | 7-10 | 3h | New tools |
| **Total** | **1-10** | **~4.5h** | |
