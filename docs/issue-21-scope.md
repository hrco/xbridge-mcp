# Issue #21 Implementation Scope — TTS, STT, Files API, Context Compaction, Batch

Scoping pass for [issue #21](../../issues/21), following the Safe-refresh precedent
(one small PR per surface, off `main`, founder-gated). Exact wire schemas are in
`xai-delta-2026-07-issue21-schemas.md`; this doc turns those into concrete tool
designs, file layout, and a PR sequence.

Acceptance criteria requires TTS+STT, Files CRUD, and Context Compaction. Batch API
is a stretch (not in the checklist) but scoped here as PR 5 per founder direction —
chat-only, since image/video batch request shapes are unconfirmed in the docs.

---

## PR 1 — `grok-tts`

**New constants:** `TTS_API_BASE = f"{_XAI_HOST}/v1/tts"`, `TTS_VOICES = ["eve", "ara", "rex", "sal", "leo"]`, `DEFAULT_TTS_VOICE = "eve"`.

**`make_tts_request(text, voice_id, language, speed, with_timestamps)`** — always sends
`with_timestamps: true` to the API internally (regardless of the tool arg), so the
response is always the JSON-with-base64-audio shape rather than raw binary — keeps
one response-parsing code path instead of branching on content-type.

**`handle_grok_tts` tool schema:**
- `text` (string, required, ≤15,000 chars)
- `voice` (enum, default `eve`)
- `language` (string, default `"auto"`)
- `speed` (number, 0.7–1.5, default `1.0`)
- `with_timestamps` (bool, default `false`) — whether the tool's text output includes the timestamp table

**Output:** `AudioContent(data=<base64>, mimeType=<content_type>)` + a `TextContent`
summary (duration, and timestamps table if requested).

**v1 cut:** no `output_format` codec/sample-rate customization (MP3 24kHz/128kbps
default only) — flag as a follow-up if a user asks for WAV/PCM.

---

## PR 2 — `grok-stt`

**New constants:** `STT_API_BASE = f"{_XAI_HOST}/v1/stt"`.

**`make_stt_request(audio_url, language, diarize, filler_words, inverse_text_norm, multichannel, channels)`**
— posts multipart with the `url` field only (the API downloads server-side). Reuses
the existing `image_url`/`video_url` tool-arg pattern instead of adding local-file
upload complexity to this tool.

**Implementation gotcha to flag for the engineer:** `httpx` multipart encoding via a
plain `data=` dict doesn't guarantee field ordering against a `files=` dict — the API
docs don't state STT's `url`-only submission has an ordering requirement (that
requirement is documented for `file` uploads specifically), so this should be fine
with `data={"url": ..., "language": ..., ...}` in a multipart POST, but worth a
close read of the STT docs' exact wording before relying on it.

**`handle_grok_stt` tool schema:**
- `audio_url` (string, required)
- `language` (string, optional)
- `diarize` (bool, default `false`)
- `filler_words` (bool, default `false`)
- `inverse_text_normalization` (bool, default `false`) → maps to API's `format` field
- `multichannel` (bool, default `false`)
- `channels` (int, optional, 2–8)

**Output:** `TextContent` — transcript, plus a speaker/word table when diarization or
multichannel was requested.

**v1 cut:** local-file (`file` field) upload path deferred — `keyterm` biasing
deferred too (delimiter format unconfirmed in docs).

---

## PR 3 — Files API (`grok-file-upload`, `grok-file-list`, `grok-file-delete`, `grok-file-public-url`)

**New constants:** `FILES_API_BASE = f"{_XAI_HOST}/v1/files"`.

- **`grok-file-upload(file_path, purpose="assistants", expires_after=None)`** — validates
  `Path(file_path).is_file()` before reading, uploads via multipart. Per the docs'
  field-order requirement (`expires_after` before `file`, `file` last), this needs a
  manually ordered multipart body rather than relying on `httpx`'s dict-merge
  behavior across `data=`/`files=` — flag as an implementation risk to verify against
  a real multipart capture, not just docs prose.
- **`grok-file-list(limit=100, order="desc", sort_by="created_at", pagination_token=None)`**
- **`grok-file-delete(file_id)`**
- **`grok-file-public-url(file_id, expires_after=None)`**

**Not built in v1:** get-metadata, get-content, revoke-public-url (not required by
the acceptance checklist's "upload, list, delete, public URL" wording) — natural
follow-up additions, same endpoint family.

---

## PR 4 — `grok-context-compact`

**New constant:** `COMPACT_API_BASE = f"{_XAI_HOST}/v1/responses/compact"`.

Scoped as a **stateless** tool (per the delta report's framing — deeper
`session_manager.py` integration is a design question for later, not required here).

**`handle_grok_context_compact` tool schema:**
- `messages` (array of `{role, content}`, required)
- `model` (enum from `AVAILABLE_MODELS`, default `DEFAULT_MODEL`)

**Output:** `TextContent` with the opaque `encrypted_content` blob, `dropped_message_count`,
and a one-line instruction on reuse (spread the returned compaction item as the
leading element of the next `/v1/responses` `input` array).

---

## PR 5 — Batch API (chat-only)

**New constant:** `BATCH_API_BASE = f"{_XAI_HOST}/v1/batches"`.

Five tools mirroring the full create → add → poll → retrieve flow (more than the
issue body's "create/get/list" wording, but that's the minimum needed for the
feature to actually be usable end-to-end):

- **`grok-batch-create(name)`**
- **`grok-batch-add-requests(batch_id, requests)`** — `requests` is a list of
  `{batch_request_id, messages, model}`; handler wraps each into the confirmed
  `{"responses": {"input": [...], "model": ...}}` shape. Chat only — image/video
  `batch_request` wrapper shapes are unconfirmed, explicitly out of scope for this PR.
- **`grok-batch-get(batch_id)`** — returns `state` (num_requests/pending/success/error)
- **`grok-batch-list(limit=20)`**
- **`grok-batch-results(batch_id, limit=100, pagination_token=None)`**

---

## Common infra (all PRs)

- One `make_*_request()` helper per surface, following the existing
  `make_image_request`/`make_video_request` pattern — own `httpx.AsyncClient`,
  `get_api_key()`, `response.raise_for_status()`.
- New test files: `tests/test_audio_tools.py` (TTS+STT), `tests/test_files_tools.py`,
  `tests/test_compaction_tools.py`, `tests/test_batch_tools.py` — mocked `httpx`,
  matching the existing `tests/test_image_tools.py` structure.
- Docs: bump the tool count in `CLAUDE.md` ("19+" → new total) after each PR,
  update `docs/wiki/Home.md`/`Setup.md` if they enumerate tools.
- Each PR independently mergeable, tested, founder-gated — same as #29-33.

## Open risks to verify during implementation (not blocking scoping)

1. STT `keyterm` delimiter format — unconfirmed, deferred rather than guessed.
2. Files-upload multipart field ordering (`expires_after` before `file`) — `httpx`'s
   `data=`/`files=` dict merge doesn't guarantee this; may need a manual multipart
   body builder.
3. Batch image/video request shapes — unconfirmed, chat-only for PR 5.
