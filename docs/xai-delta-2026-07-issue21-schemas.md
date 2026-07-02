# xAI API Wire Schemas — Issue #21 Surfaces (2026-07-01)

Source: `docs.x.ai` pages fetched directly via WebFetch (no docs MCP server was
available in this environment — `ListMcpResourcesTool` returned no `docs.x.ai`
entries, so pages were read directly). Research-only, no code changes, no API calls.

## Confirmed vs unconfirmed

- **TTS** — confirmed: request fields, voice enum, response shape (both binary and
  JSON-with-timestamps variants).
- **STT** — confirmed: multipart field names, response shape. `keyterm` format
  ("max 100 terms, each up to 50 chars") reads like a delimited string but the
  exact delimiter (comma? repeated field?) is UNCONFIRMED — page prose only, no
  verbatim multipart example shown.
- **Files API** — confirmed: upload, list, get, delete, get-content, create-public-url,
  revoke-public-url — all with exact paths and response shapes.
- **Context Compaction** — confirmed: request/response shape, and the reinjection
  pattern (spread `output` into next `input`).
- **Batch API** — confirmed: create/add-requests/get/list/results paths. The
  `batch_request` wrapper's per-type keys beyond `responses` (i.e. exact field
  names for `image_generation`/`video_generation` request bodies) are UNCONFIRMED
  — the fetched page only showed the `responses` type in full; image/video batch
  request body shapes need a follow-up fetch of `/developers/rest-api-reference/`
  batch pages before those code paths are implemented (chat-only batch is fully
  confirmed and sufficient for a first PR).

---

## 1. Text-to-Speech

**`POST https://api.x.ai/v1/tts`**

| Field | Type | Required | Default | Notes |
|---|---|---|---|---|
| `text` | string | yes | — | max 15,000 chars, supports speech tags (`[pause]`, `<whisper>`) |
| `voice_id` | string | no | `"eve"` | enum: `eve`, `ara`, `rex`, `sal`, `leo` (case-insensitive) |
| `language` | string | yes | — | BCP-47 code (e.g. `en`, `zh`) or `"auto"` |
| `output_format` | object | no | MP3 24kHz/128kbps | codec/sample_rate/bit_rate config |
| `speed` | number | no | `1.0` | range 0.7–1.5 |
| `optimize_streaming_latency` | integer | no | `0` | 0, 1, or 2 |
| `text_normalization` | boolean | no | `false` | |
| `with_timestamps` | boolean | no | `false` | switches response to JSON (see below) |

Response — **without** `with_timestamps`: raw audio bytes (binary, content-type per `output_format`).

Response — **with** `with_timestamps: true`:
```json
{
  "audio": "<base64-encoded audio>",
  "content_type": "audio/mpeg",
  "duration": 0.92,
  "audio_timestamps": {
    "graph_chars": ["H", "e", "l", "l", "o"],
    "graph_times": [[0.00, 0.06], [0.06, 0.12]]
  }
}
```

Implementation note: since a Python MCP tool needs a JSON-serializable response either
way, requesting `with_timestamps: true` unconditionally (or always base64-encoding the
raw binary response) avoids branching on content-type — worth deciding at implementation
time, not blocking.

---

## 2. Speech-to-Text

**`POST https://api.x.ai/v1/stt`** — `multipart/form-data`

| Field | Type | Required | Notes |
|---|---|---|---|
| `file` | file | yes† | max 500MB; **must be the last field in the multipart body** |
| `url` | string | yes† | server-side download; alternative to `file` |
| `audio_format` | string | no | `pcm`/`mulaw`/`alaw` — raw audio only |
| `sample_rate` | integer | no | Hz, required if using raw audio |
| `language` | string | no | e.g. `en`, `fr` |
| `format` | boolean | no, default `false` | inverse-text-normalization; requires `language` when `true` |
| `multichannel` | boolean | no, default `false` | |
| `channels` | integer | no | 2–8, raw audio only |
| `diarize` | boolean | no, default `false` | |
| `keyterm` | string | no | max 100 terms, each ≤50 chars — delimiter UNCONFIRMED |
| `filler_words` | boolean | no, default `false` | include "uh"/"um"/"er" |

† exactly one of `file` or `url` required.

Response:
```json
{
  "text": "string",
  "language": "string",
  "duration": 0.0,
  "words": [
    {"text": "string", "start": 0.0, "end": 0.0, "speaker": 0}
  ],
  "channels": []
}
```
`speaker` only present when `diarize: true`; `channels` only present when `multichannel: true`.

Supported containers: WAV, MP3, OGG, Opus, FLAC, AAC, MP4, M4A, MKV. Raw: PCM, µ-law, A-law.

---

## 3. Files API

All under `https://api.x.ai/v1/files`.

### Upload
**`POST /v1/files`** — multipart

| Field | Required | Notes |
|---|---|---|
| `file` | yes | binary content — **must appear last in the multipart body** |
| `purpose` | yes | string, conventionally `"assistants"` |
| `expires_after` | no | int seconds (3600–2592000) or `{"anchor": "created_at", "seconds": <int>}` — must appear *before* `file` in the body |

Response:
```json
{
  "id": "file_<uuid>",
  "filename": "string",
  "bytes": 0,
  "created_at": 0,
  "expires_at": null,
  "object": "file",
  "purpose": "string"
}
```

### List
**`GET /v1/files`** — query params (all optional): `limit` (max 100, default 100),
`order` (`asc`/`desc`, default `desc`), `sort_by` (`created_at`/`filename`/`size`,
default `created_at`), `pagination_token`.

Response:
```json
{
  "data": [ { "...": "same shape as upload response" } ],
  "pagination_token": "string"
}
```

### Get metadata
**`GET /v1/files/{file_id}`** → single file object (same shape as upload response).

### Get content
**`GET /v1/files/{file_id}/content`** → raw binary bytes, streamed.

### Delete
**`DELETE /v1/files/{file_id}`**
```json
{ "id": "string", "deleted": true }
```

### Create public URL
**`POST /v1/files/{file_id}/public-url`**
Request body: `{"expires_after": <int seconds, optional>}` — must be between 3600
and 2,592,000 if provided.
Response:
```json
{ "public_url": "https://files-cdn.x.ai/<token>/file_abc123.png" }
```
Idempotent while the URL is active — repeat calls return the same URL. Max file
size for public URLs: 50 MiB (larger files stay available via the authenticated
content endpoint only). Max 1,000 active public URLs per team.

### Revoke public URL
**`POST /v1/files/{file_id}/public-url/revoke`** — no body.
```json
{ "id": "file_abc123", "revoked": true, "public_url": "https://files-cdn.x.ai/..." }
```
Safe to call again — returns `revoked: false` if already revoked/never existed.

---

## 4. Context Compaction

**`POST https://api.x.ai/v1/responses/compact`**

Request:
```json
{
  "model": "grok-4.3",
  "input": [
    {"role": "system", "content": "..."},
    {"role": "user", "content": "..."},
    {"role": "assistant", "content": "..."}
  ]
}
```

Response:
```json
{
  "id": "cmp_<uuid>",
  "object": "response.compaction",
  "output": [
    {"type": "compaction", "id": "cmp_<uuid>", "encrypted_content": "<opaque blob>"}
  ],
  "usage": {
    "input_tokens": 0,
    "output_tokens": 0,
    "dropped_message_count": 0
  }
}
```

Reuse pattern: spread `output` (the compaction item(s)) as the leading element(s)
of the next `/v1/responses` call's `input` array, followed by new messages.
`encrypted_content` is opaque — must be passed back verbatim, never parsed/modified.

---

## 5. Batch API

All under `https://api.x.ai/v1/batches`.

### Create batch
**`POST /v1/batches`**
Request: `{"name": "customer_feedback_analysis"}`
Response (partial, per docs excerpt): `{"batch_id": "...", "name": "..."}`

### Add requests
**`POST /v1/batches/{batch_id}/requests`**
```json
{
  "batch_requests": [
    {
      "batch_request_id": "feedback_001",
      "batch_request": {
        "responses": {
          "input": [
            {"role": "system", "content": "..."},
            {"role": "user", "content": "..."}
          ],
          "model": "grok-4.3"
        }
      }
    }
  ]
}
```
`batch_request` is a wrapper keyed by operation type — `responses` confirmed in full;
`image_generation`/`video_generation`/etc. field shapes are **UNCONFIRMED** (need a
follow-up fetch of `/developers/rest-api-reference/` batch pages).

### Get batch status
**`GET /v1/batches/{batch_id}`**
```json
{
  "batch_id": "...",
  "state": {
    "num_requests": 100,
    "num_pending": 25,
    "num_success": 70,
    "num_error": 5
  }
}
```
(Issue-#21 research doc also lists `num_cancelled` at the batch level and per-request
states `pending/succeeded/failed/cancelled` — not contradicted here, just not shown
in this page's excerpt.)

### List batches
**`GET /v1/batches?limit=20`**
```json
{ "batches": [ { "batch_id": "...", "name": "...", "state": {"num_requests": 0, "num_pending": 0} } ] }
```

### Retrieve results
**`GET /v1/batches/{batch_id}/results?limit=100&pagination_token={token}`**
```json
{
  "results": [
    {
      "batch_request_id": "feedback_001",
      "batch_result": {
        "response": { "chat_get_completion": {} }
      }
    }
  ],
  "pagination_token": "..."
}
```
`batch_result.response` is keyed by type (`chat_get_completion`, `image_response`,
`video_response`) depending on what was submitted.
