# xAI API Delta Report — 2026-07-01

Source of truth: `https://docs.x.ai/api/mcp` (docs MCP, live), diffed against
`xbridge_mcp/server.py` as of this commit. Scope: research only, no code changes here.
Goal: feed 4 GitHub issues for the "Safe refresh" — keep all 19 tool contracts stable,
additive/corrective changes only.

---

## #18 — Stale model pricing, context sizes, missing models (`handle_grok_models`, `AVAILABLE_MODELS`)

**Touchpoints:** `AVAILABLE_MODELS` (server.py:41-57), `handle_grok_models()` (server.py:1210-1271),
`DEFAULT_MODEL` (server.py:40).

> **Note on `DEFAULT_MODEL = "grok-4-1-fast"`**: this is xBridge's fallback model for every
> chat/text tool. The May-15-2026 retirement doc lists `grok-4-1-fast-reasoning` and
> `grok-4-1-fast-non-reasoning` as retired→redirected to `grok-4.3`; the plain `grok-4-1-fast`
> slug isn't named explicitly, so its exact post-retirement behavior is unconfirmed. Given
> the whole 4-1-fast line is being sunset, consider moving `DEFAULT_MODEL` to `grok-4.3` (the
> docs' explicitly-recommended default). Flagged for #18 — verify slug liveness first.

### What xBridge has now

```python
AVAILABLE_MODELS = [
    "grok-4.20-0309-reasoning", "grok-4.20-0309-non-reasoning", "grok-4.20-multi-agent-0309",
    "grok-4.3",
    "grok-4", "grok-4-1-fast",
    "grok-3-fast", "grok-3-mini", "grok-2", "grok-2-latest", "grok-2-vision-1212",
]
```
`handle_grok_models` hardcodes a markdown table: grok-4.20 family @ 2M context, $2.00/$6.00
(cached $0.20); grok-4.3 @ 1M, $1.25/$2.50; grok-4 @ 256K, $3.00/$15.00; grok-4-1-fast @ 2M,
$0.20/$0.50; grok-3-fast @ 131K, $0.30/$0.50; grok-2/grok-2-latest @ 32K, $2.00/$10.00;
grok-2-vision-1212 @ 32K, $2.00/$10.00.

### What xAI docs say now (`/developers/models`, `/developers/pricing`)

Current model pricing table (the only models xAI's docs price today):

| Model | Context | Input/1M | Output/1M |
|---|---|---|---|
| `grok-4.3` | **1M** | $1.25 | $2.50 |
| `grok-4.20-0309-reasoning` | **1M** | $1.25 | $2.50 |
| `grok-4.20-0309-non-reasoning` | **1M** | $1.25 | $2.50 |
| `grok-4.20-multi-agent-0309` | **1M** | $1.25 | $2.50 |
| `grok-build-0.1` (new — coding model) | 256K | $1.00 | $2.00 |

No `grok-4`, `grok-4-1-fast`, `grok-3-fast`, `grok-3-mini`, `grok-2`, `grok-2-latest`, or
`grok-2-vision-1212` appear in the current pricing table at all.

`/developers/migration/may-15-retirement` (effective **May 15, 2026, 12:00 PM PT** — already
past as of today 2026-07-01) confirms why: these are **retired**, not merely re-priced:

* Retired → auto-redirect to `grok-4.3` (billed at `grok-4.3` rates, not their old rates):
  `grok-4-1-fast-reasoning`, `grok-4-1-fast-non-reasoning`, `grok-4-fast-reasoning`,
  `grok-4-fast-non-reasoning`, `grok-4-0709`, `grok-3` → `grok-4.3` (reasoning effort
  `low`/`none` depending on variant).
  `grok-code-fast-1` → `grok-build-0.1`.
  `grok-imagine-image-pro` → `grok-imagine-image-quality`.
* Note the retirement list uses different exact slugs than xBridge's `AVAILABLE_MODELS`
  (`grok-4-1-fast-reasoning`/`-non-reasoning` vs xBridge's plain `grok-4-1-fast`; `grok-4-0709`
  vs xBridge's plain `grok-4`; `grok-3` vs xBridge's `grok-3-fast`/`grok-3-mini`). Could not
  confirm from docs whether xBridge's exact slugs (`grok-4`, `grok-4-1-fast`, `grok-3-fast`,
  `grok-3-mini`, `grok-2`, `grok-2-latest`, `grok-2-vision-1212`) still resolve at all post
  May-15 — **flagging as unknown**, docs don't enumerate legacy-slug aliasing beyond the
  table above.
* `grok-4.3`: 1M context, 4 reasoning-effort levels (`none`/`low`/`medium`/`high`), $1.25/$2.50.
* Notable: `logprobs`/`top_logprobs` are **silently ignored** on `grok-4.20`+ models — no error,
  just no-op. Worth a doc note wherever xBridge exposes those params (grep showed none, but
  double-check tool schemas before closing the issue).

### The gap

1. **Context window wrong for the whole 4.20 family + grok-4.3**: xBridge says 2M, docs say 1M
   (grok-4.20-*) and 1M (grok-4.3, xBridge already had 1M right there — consistent).
   → Actually xBridge already lists grok-4.3 at 1M correctly; the 2M number is wrong on the
   THREE grok-4.20-* entries.
2. **Missing `grok-build-0.1`** — new coding-focused model (256K, $1.00/$2.00), replaces
   `grok-code-fast-1`. Not in `AVAILABLE_MODELS` at all.
3. **Pricing wrong on multiple legacy entries**: grok-4.20 family priced $2.00/$6.00 (cached
   $0.20) in xBridge vs $1.25/$2.50 flat in current docs. grok-4 ($3.00/$15.00, 256K) and
   grok-4-1-fast ($0.20/$0.50, 2M) don't appear in the current pricing table at all — likely
   retired/redirected per the May-15 doc, meaning both price AND context claims are stale.
4. **Legacy models (`grok-3-fast`, `grok-3-mini`, `grok-2`, `grok-2-latest`,
   `grok-2-vision-1212`) have no corresponding entries in current docs** — could not confirm
   whether these still work, are silently redirected, or 404. Docs only explicitly discuss
   `grok-3` (not `-fast`/`-mini` variants) as retired→redirected. **Unknown, flag for #18
   follow-up** — may need a support ticket or live (non-billed) test rather than doc-only
   verification.

### Breaking vs additive

- Adding `grok-build-0.1` to `AVAILABLE_MODELS`: **additive**.
- Correcting context/pricing text in `handle_grok_models`: **additive** (docs-only change,
  doesn't alter the tool's enum/schema, just the informational payload).
- Removing retired model slugs from `AVAILABLE_MODELS`/enum: **breaking** for any caller
  currently passing those slugs — recommend keeping them in the enum (they still resolve,
  per the redirect note) but flagging in `handle_grok_models` output that they're
  deprecated/redirected, rather than deleting them outright.

---

## #19 — Media models, video "failed" status, 1080p, `enable_image_search`

**Touchpoints:** `IMAGE_MODELS`, `VIDEO_MODELS`, `ASPECT_RATIOS_IMAGE/VIDEO`,
`VIDEO_RESOLUTIONS` (server.py:64-86), whichever handler builds video status polling / image
generation request bodies (not yet located precisely — grep for `VIDEO_RESOLUTIONS` and the
image/video handler functions before implementing).

### What xBridge has now

```python
IMAGE_MODELS = ["grok-imagine-image", "grok-2-image-1212"]
VIDEO_MODELS = ["grok-imagine-video"]
VIDEO_RESOLUTIONS = ["480p", "720p"]
```
Confirmed by code read: xBridge's web-search and x-search handlers support
`enable_image_understanding` (server.py:527, 590 schemas; 1146-1147, 1189-1190 handlers) but
**not `enable_image_search`** — the image-search param is entirely absent.

### What xAI docs say now

**Imagine Pricing** (`/developers/pricing`, `/developers/models`):

| Model | Cost |
|---|---|
| `grok-imagine-image` | $0.02/image |
| `grok-imagine-image-quality` | $0.05/image |
| `grok-imagine-video` | $0.050/sec |
| `grok-imagine-video-1.5` | $0.080/sec |

`grok-imagine-image-pro` is retired → redirects to `grok-imagine-image-quality` (per
migration doc). `grok-2-image-1212` does not appear anywhere in current docs (pricing,
models, or generation pages) — likely legacy/unlisted, **unknown status, flag**.

**Video status values** (`/developers/model-capabilities/video/generation`): the async
poll returns `status` ∈ `pending | done | expired | failed` (not just done/pending) — a
`failed` result includes an `error` object with `code` (`invalid_argument`,
`permission_denied`, `failed_precondition`, `service_unavailable`, `internal_error`) and
`message`. There's also an `expired` state, distinct from `failed`.

**Resolution**: video resolutions are `480p` (default), `720p`, `1080p`. **1080p is
gated**: "only supported on `grok-imagine-video-1.5` for image-to-video generation" — not
available on `grok-imagine-video` or for plain text-to-video.

**Image resolution** (separate axis, images not video): `1k` / `2k` via `resolution` param
on `grok-imagine-image-quality` — xBridge doesn't appear to expose an image `resolution`
param at all (only aspect ratio was visible in the excerpt read).

**`enable_image_search`**: confirmed via docs search — it's a `web_search` tool parameter
(not an image-generation param): "Enable image search results that can be embedded in
responses" alongside `enable_image_understanding` ("Enable analysis of images found during
browsing"). Lives on `/developers/tools/web-search`. Grok can then embed images as Markdown
in responses (`/developers/tools/citations` — "Image Embeds" section).

### The gap

1. **Missing `grok-imagine-image-quality`** and **`grok-imagine-video-1.5`** from
   `IMAGE_MODELS`/`VIDEO_MODELS` — these are the current top-tier/recommended models per docs
   (all Imagine examples in docs use `-quality` and reference `-1.5` for image-to-video).
2. **`grok-2-image-1212`** in xBridge has no doc presence — likely dead weight, needs
   verification (test call or support) before removal (removal would be breaking if still
   live).
3. **`VIDEO_RESOLUTIONS = ["480p", "720p"]`** is missing `1080p` (additive, but must gate it
   to `grok-imagine-video-1.5` + image-to-video mode only — naive addition would let callers
   request unsupported combos that 400).
4. **Video status handling — confirmed bug**: the polling loop (server.py:326-355) handles
   `done` and `expired` but **not `failed`**. A `failed` result (which per docs carries a
   structured `error.code`/`error.message`) falls through the `if/elif`, the loop keeps
   polling a dead request, and the caller only gets a generic `TimeoutError` after the full
   `VIDEO_POLL_TIMEOUT` (600s) — a 10-minute hang on what xAI already reported as an instant
   failure, with the useful `error.code`/`message` thrown away. Should add an explicit
   `elif status == "failed"` branch that surfaces `error.code`/`error.message`.
5. **No `enable_image_search` / `enable_image_understanding` params surfaced** on whatever
   xBridge tool wraps web search — additive if absent.
6. Image **aspect ratios**: docs list `19.5:9`/`9:19.5` and `20:9`/`9:20` for images —
   xBridge's `ASPECT_RATIOS_IMAGE` already includes these, so no gap there. Video aspect
   ratios in docs (`1:1, 16:9, 9:16, 4:3, 3:4, 3:2, 2:3`) match xBridge's
   `ASPECT_RATIOS_VIDEO` exactly — no gap.

### Breaking vs additive

- Adding `grok-imagine-image-quality`, `grok-imagine-video-1.5`, `1080p` resolution:
  **additive**.
- Handling `expired`/`failed` status distinctly in polling: **additive** (currently
  presumably falls through to a generic error or timeout — improves error messages, doesn't
  change the tool's public contract).
- Removing `grok-2-image-1212`: **potentially breaking** — verify liveness first.

---

## #20 — Priority Processing (`service_tier`) + Cost Tracking (`cost_in_usd_ticks`)

**Touchpoints:** `make_grok_request()` (server.py:122-177, the shared request builder — the
single choke point where `service_tier` would be threaded into the payload), and
`extract_response_text()` (server.py:358-395, where `cost_in_usd_ticks` would be read off the
`usage` object). `usage_tracker` (imported server.py:34, from `token_counter.py`) already
accumulates token usage in `make_grok_request` (server.py:179-181) — the natural home for a
cost accumulator.

### What xBridge has now (confirmed by code read)

`make_grok_request()` (server.py:122-177) builds the payload with only `model`, `input`, and
(optionally) `tools` — **no `service_tier` field, no path to pass one through**.
`extract_response_text()` (server.py:358-395) reads only the `output` text items and
**discards the `usage` object entirely** — `cost_in_usd_ticks` (and token counts) never reach
the caller. Confirmed: neither surface exists today.

### What xAI docs say now (`/developers/advanced-api-usage/priority-processing`,
`/developers/cost-tracking`)

**Priority Processing**: add `service_tier: "priority"` to any Chat Completions / Responses
request body — no reservation needed. Response echoes back `service_tier` (`"default"` or
`"priority"`) so caller can confirm what was actually billed. **2x price premium** applies to
all token types (input/output/cached/reasoning), cache discounts applied before the
multiplier. **Not supported** for image generation, video generation, or Batch API. Billing
only happens when response confirms `"priority"` — if request falls back to default tier,
standard rates apply (i.e., it's opportunistic, not guaranteed).

**Cost Tracking**: every inference response (chat completions, Responses API, image gen,
video gen) includes `usage.cost_in_usd_ticks` — the exact per-request cost already billed,
post-discount, inclusive of tool invocation costs. 1 USD = 10,000,000,000 ticks
(`cost_usd = cost_in_usd_ticks / 1e10`). For streaming, cost only appears on the final chunk
(REST/OpenAI-SDK: requires `stream_options: {include_usage: true}`; xAI SDK exposes it
automatically). Batch results carry per-result costs too, plus a batch-level
`cost_breakdown.total_cost_usd_ticks`.

### The gap

1. **No `service_tier` param exposed** on any xBridge chat/text tool schema — pure addition:
   an optional `service_tier: "default" | "priority"` field passed through to the xAI request
   body, plus the response should surface which tier xAI actually used.
2. **No cost surfacing** — xBridge doesn't appear to extract/report `cost_in_usd_ticks` from
   responses back to the MCP caller. Given `token_counter.py` / `usage_tracker` already
   exists in the codebase (imported in server.py:34) for token accounting, this is a natural
   extension point — worth checking whether `usage_tracker` already has a slot for cost that
   just isn't populated, vs needing a new field.
3. Must **not** offer `service_tier: "priority"` on image/video tool schemas (docs explicitly
   say unsupported there) — a schema-design consideration for the mcp-specialist agent.

### Breaking vs additive

- Both are pure additions to request/response shape — **additive**, no existing behavior
  changes if `service_tier` is omitted (docs confirm omitting the field = default behavior)
  and cost reporting is just extra text in the tool response.

---

## #21 — New surfaces: TTS, STT, Files API, Context Compaction, Batch

None of these five surfaces have any handler in `server.py` today (no `handle_grok_tts`,
`handle_grok_stt`, `handle_grok_files_*`, `handle_grok_compact`, or `handle_grok_batch_*`
found by symbol name in the sections read) — these are pure net-new tool candidates, not
corrections to existing tools. Per the "Safe refresh" framing (keep 19 tool contracts
stable), these should be scoped as **separate future tools**, not touchpoints on existing
handlers.

### Text-to-Speech (`/developers/model-capabilities/audio/text-to-speech`,
`/developers/models/text-to-speech`)
- `POST https://api.x.ai/v1/tts` — text (max 15,000 chars) → audio bytes.
- 5 voices (`eve` default, `ara`, `rex`, `sal`, `leo`), speech tags (`[pause]`, `<whisper>`),
  20 supported languages + `auto`, configurable codec/sample-rate/bit-rate (mp3/wav/pcm/
  mulaw/alaw), optional character-level timestamps (`with_timestamps`), custom voice cloning.
  Also a bidirectional WebSocket streaming variant (`wss://api.x.ai/v1/tts`) with no length
  limit, barge-in support (`text.clear`), 50 concurrent sessions/team cap.
- Pricing: $15.00 / 1M characters.

### Speech-to-Text (`/developers/model-capabilities/audio/speech-to-text`,
`/developers/models/speech-to-text`)
- `POST https://api.x.ai/v1/stt` — multipart upload (`file` or `url`), max 500MB, 12 audio
  formats, up to 8 channels (multichannel), diarization, keyterm biasing, filler-word
  control, inverse-text-normalization (`format=true` + `language`).
- WebSocket streaming variant (`wss://api.x.ai/v1/stt`) with interim results, Smart Turn
  end-of-turn ML detection, multichannel streaming.
- Pricing: $0.10/hr REST, $0.20/hr streaming.

### Files API (`/developers/files`, `/developers/files/managing-files`)
- Chat with attached files (public URL or uploaded file ID) auto-activates an
  `attachment_search` server-side tool → agentic document search/reasoning.
- Upload/list/retrieve/delete via REST; max 48MB/file for chat-attachment use (separate
  storage-oriented Files API endpoints — upload/download/manage — exist too, at
  $0.025/GiB/day storage, $0.20/GiB download).
- Supported formats: txt, md, code files, csv, json, pdf, "many other text-based formats."
- Requires agentic-capable models (`grok-4.20`, `grok-4.3` — explicitly named in docs).
- No batch support for file-attached chats (`n > 1` unsupported there).
- Distinct from **Collections** (persistent semantic-search document stores) — separate doc
  tree (`developers/files/collections/*`), not covered in this pass; flag as a further-out
  surface if #21 wants full parity.

### Context Compaction (`/developers/advanced-api-usage/context-compaction`)
- `POST https://api.x.ai/v1/responses/compact` — takes a message array, returns a single
  opaque `compaction` item (`encrypted_content`) that replaces the whole prior conversation
  for the next `/v1/responses` call. Must be passed back verbatim, never edited/reordered.
  One compaction per call; conversation must already fit in context (compaction shrinks, it
  doesn't rescue over-limit requests). `xai_sdk` also has `chat.compact()` for in-place
  compaction of a live `Chat` object.
- Directly relevant to xBridge's existing `session_manager.py` — this could plug into
  long-running session chat tools to cut cost on multi-turn sessions, but that's a design
  question for the engineer, not something to resolve here.

### Batch API (`/developers/advanced-api-usage/batch-api`)
- 4-step flow: create batch → add requests (chat/image/edit/video/video-edit/video-extend/
  remote-MCP, each tagged with a `batch_request_id`) → poll `num_pending` → retrieve paginated
  results. Also supports JSONL file upload as an alternative to inline requests (max 200MB /
  50,000 requests per file).
- Discounted pricing: 20-50% off standard token rates (image/video billed at standard rates
  even in batch). Not subject to per-minute rate limits. Typically completes within 24h
  (best-effort, not guaranteed).
- Batch-level state: `num_requests/num_pending/num_success/num_error/num_cancelled`.
  Request-level state: `pending/succeeded/failed/cancelled`.
- Limits: 2 batch creations/sec/team, 25MB max per individual batch request, 1000
  add-requests calls/30s/team (rolling), signed result URLs for media expire after 1 hour.

### Breaking vs additive

All five are **net-new, purely additive** tool candidates — zero interaction with the
existing 19 tool contracts. No existing xBridge code touches any of these surfaces today.

---

## Summary (for the 4 issues)

- **#18**: `AVAILABLE_MODELS`/`handle_grok_models` context-window claims are wrong for the
  entire grok-4.20 family (1M not 2M per current docs), `grok-build-0.1` is missing entirely,
  and several legacy slugs (`grok-4`, `grok-4-1-fast`, `grok-3-fast`, `grok-3-mini`, `grok-2`,
  `grok-2-latest`, `grok-2-vision-1212`) have no presence in current pricing/model docs —
  status unconfirmed (retired-and-redirected per the May-15-2026 migration doc, or simply
  undocumented-but-live — could not tell from docs alone).
- **#19**: `grok-imagine-image-quality` and `grok-imagine-video-1.5` (current recommended
  media models) are missing from `IMAGE_MODELS`/`VIDEO_MODELS`; `1080p` video resolution
  exists but is gated to `-1.5` + image-to-video only; video status has `expired`/`failed`
  states with structured error codes that may not be handled; `grok-2-image-1212`'s doc
  presence could not be confirmed at all; `enable_image_search`/`enable_image_understanding`
  are real `web_search` tool params, confirmed via docs search, not yet located in xBridge's
  web-search tool schema.
- **#20**: `service_tier: "priority"` (2x premium, opt-in, chat/responses only — not
  image/video/batch) and `usage.cost_in_usd_ticks` (present on every inference response
  including image/video) are both entirely absent from xBridge today — pure additive
  surfacing, no existing behavior changes required.
- **#21**: TTS (`/v1/tts`), STT (`/v1/stt`), Files API (`attachment_search` auto-agentic
  chat-with-files), Context Compaction (`/v1/responses/compact`), and Batch API
  (`/v1/batches`) are five fully net-new surfaces with zero existing xBridge code — each a
  candidate for a new tool, none touching the 19 existing tool contracts.

### Top risks/unknowns to flag before implementation

1. **Legacy model slug liveness** (#18) — docs don't confirm whether `grok-4`, `grok-4-1-fast`,
   `grok-3-fast`, `grok-3-mini`, `grok-2`, `grok-2-latest`, `grok-2-vision-1212` still resolve
   post-May-15-2026 retirement, or 404/redirect silently. Needs a live (low-cost) API probe,
   not doc research, to resolve definitively.
2. **`grok-2-image-1212` status** (#19) — zero doc presence found (pricing, models, or
   generation pages); same live-probe caveat applies before deciding to keep or drop it.
3. **Collections API** (`developers/files/collections/*`) was spotted in the doc index but not
   fetched — if #21 wants "Files API" to include persistent semantic-search collections (not
   just per-chat attachments), that's an additional doc-research pass needed.

_Resolved during this pass (were unknowns, now confirmed by code read): video-polling
`failed`-status bug (server.py:326-355), `enable_image_search` absence (only
`enable_image_understanding` exists), and the exact `service_tier`/`cost_in_usd_ticks`
touchpoints (`make_grok_request` / `extract_response_text`)._
