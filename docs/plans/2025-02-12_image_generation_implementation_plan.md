# Image & Video Generation Implementation Plan

> **Date**: 2025-02-12
> **Author**: grok-mcp-expert agent
> **Status**: Ready for Implementation
> **Target Version**: 2.0.0

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Architecture Decision](#2-architecture-decision)
3. [API Reference (xAI Image & Video)](#3-api-reference)
4. [New MCP Tool Designs](#4-new-mcp-tool-designs)
5. [Implementation Code](#5-implementation-code)
6. [Updated Constants & Models](#6-updated-constants--models)
7. [MCP Response Strategy (Images via MCP)](#7-mcp-response-strategy)
8. [Testing Strategy](#8-testing-strategy)
9. [Configuration & Environment Changes](#9-configuration--environment-changes)
10. [Migration Checklist](#10-migration-checklist)

---

## 1. Executive Summary

This plan adds **4 new MCP tools** to the Grok MCP Server:

| New Tool | xAI Endpoint | Description |
|----------|-------------|-------------|
| `grok-image-generate` | `POST /v1/images/generations` | Text-to-image generation |
| `grok-image-edit` | `POST /v1/images/edits` | Edit existing images with prompts |
| `grok-image-models` | (local) | List available image/video models |
| `grok-video-generate` | `POST /v1/videos/generations` + `GET /v1/videos/{id}` | Text/image-to-video generation |

This brings the server from **12 tools** to **16 tools** and from **6 models** to **12+ models**.

---

## 2. Architecture Decision

### Decision: Extend `server.py` (DO NOT create separate `image_server.py`)

### Rationale

1. **Single MCP Server Pattern** -- The project follows a "one server, many tools" design. All 12 current tools live in `server.py` with a single `@server.call_tool()` dispatcher. Adding image tools is consistent with this pattern.

2. **Shared Authentication** -- Both image and text APIs use the same `XAI_API_KEY` and `Bearer` auth. A separate server would duplicate this boilerplate.

3. **Shared Client Infrastructure** -- The `httpx.AsyncClient` pattern, error handling, and timeout config are reusable. Only the endpoint URL and payload structure differ.

4. **Tool Discovery** -- MCP clients (Claude Code) see all tools from one server config entry. Splitting into two servers forces users to configure two MCP server entries in their `claude_desktop_config.json` / settings.

5. **Chain Integration** -- Future chains (e.g., "search for reference image -> generate similar image -> edit with style transfer") benefit from all tools being in the same server process.

### What DOES Change

- A **new function** `make_image_request()` is added alongside `make_grok_request()` because the image API uses a completely different endpoint (`/v1/images/generations` vs `/v1/responses`), different request schema (no `input` array), and different response format (image URLs/base64 instead of nested output).
- A **new function** `make_video_request()` is added for the video async workflow (submit + poll pattern).
- The `AVAILABLE_MODELS` list is expanded with image and video model entries.
- The `handle_grok_models` handler is updated to include image/video model info.

### File Impact Summary

| File | Change Type | Description |
|------|------------|-------------|
| `server.py` | **MODIFY** | Add new constants, functions, tool definitions, handlers |
| `session_manager.py` | No change | Not involved in image generation |
| `tool_chains.py` | No change (v2.0) | Future: add image chains in later release |
| `__init__.py` | **MODIFY** | Bump version to 2.0.0 |
| `pyproject.toml` | **MODIFY** | Update description, bump version |

---

## 3. API Reference (xAI Image & Video)

### 3.1 Image Generation Endpoint

```
POST https://api.x.ai/v1/images/generations
Content-Type: application/json
Authorization: Bearer $XAI_API_KEY
```

**Request Body:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `prompt` | string | Yes | -- | Text description of the desired image |
| `model` | string | No | `"grok-imagine-image"` | Model ID |
| `n` | integer | No | `1` | Number of images (1-10) |
| `response_format` | string | No | `"url"` | `"url"` or `"b64_json"` (cURL/raw HTTP) |
| `image_format` | string | No | `"url"` | `"url"` or `"base64"` (SDK format, alias) |
| `aspect_ratio` | string | No | `"auto"` | See aspect ratio enum below |

**Aspect Ratio Enum:**
`"1:1"`, `"16:9"`, `"9:16"`, `"4:3"`, `"3:4"`, `"3:2"`, `"2:3"`, `"2:1"`, `"1:2"`, `"19.5:9"`, `"9:19.5"`, `"20:9"`, `"9:20"`, `"auto"`

**Response (URL format, single image):**
```json
{
  "url": "https://...",
  "model": "grok-imagine-image",
  "respect_moderation": true
}
```

**Response (base64 format, single image):**
```json
{
  "image": "<base64_jpeg_data>",
  "model": "grok-imagine-image",
  "respect_moderation": true
}
```

**Response (batch, n>1):** Array of the above objects.

**IMPORTANT Notes:**
- Use `response_format: "b64_json"` for raw HTTP / cURL requests
- Use `image_format: "base64"` for SDK-style requests
- We will use `response_format` in our implementation for raw HTTP
- URLs are **temporary** -- download promptly
- Content moderation applied; check `respect_moderation` field
- No `mask` parameter (unlike DALL-E)

### 3.2 Image Editing Endpoint

```
POST https://api.x.ai/v1/images/edits
Content-Type: application/json
Authorization: Bearer $XAI_API_KEY
```

**Request Body:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `prompt` | string | Yes | -- | Description of desired changes |
| `model` | string | No | `"grok-imagine-image"` | Model ID |
| `image_url` | string | Yes | -- | Source image: public URL or `data:image/jpeg;base64,...` |
| `response_format` | string | No | `"url"` | `"url"` or `"b64_json"` |
| `n` | integer | No | `1` | Number of edited variations |

**IMPORTANT:** `multipart/form-data` is NOT supported. Must use `application/json` with `image_url` field.

### 3.3 Video Generation Endpoint (Async)

```
POST https://api.x.ai/v1/videos/generations
Content-Type: application/json
Authorization: Bearer $XAI_API_KEY
```

**Request Body:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `model` | string | Yes | -- | `"grok-imagine-video"` |
| `prompt` | string | Yes | -- | Text description of the video |
| `image_url` | string | No | -- | Source image for image-to-video |
| `video_url` | string | No | -- | Source video for video editing (max 8.7s) |
| `duration` | integer | No | varies | 1-15 seconds |
| `aspect_ratio` | string | No | `"16:9"` | `"1:1"`, `"16:9"`, `"9:16"`, `"4:3"`, `"3:4"`, `"3:2"`, `"2:3"` |
| `resolution` | string | No | `"480p"` | `"480p"` or `"720p"` |

**Submit Response:**
```json
{ "request_id": "d97415a1-5796-b7ec-379f-4e6819e08fdf" }
```

**Poll Endpoint:**
```
GET https://api.x.ai/v1/videos/{request_id}
Authorization: Bearer $XAI_API_KEY
```

**Poll Response (done):**
```json
{
  "status": "done",
  "video": {
    "url": "https://vidgen.x.ai/.../video.mp4",
    "duration": 8,
    "respect_moderation": true
  },
  "model": "grok-imagine-video"
}
```

**Statuses:** `"pending"`, `"done"`, `"expired"`

### 3.4 Available Models

| Model | Type | Input | Output | Price | Rate Limit |
|-------|------|-------|--------|-------|------------|
| `grok-imagine-image` | Image Gen + Edit | text, image | image | $0.02/img | 300 RPM |
| `grok-imagine-image-pro` | Premium Image Gen | text, image | image | $0.07/img | 30 RPM |
| `grok-2-image-1212` | Legacy Text-to-Image | text | image | $0.07/img | 300 RPM |
| `grok-imagine-video` | Video Gen | text, image, video | video | $0.05/sec | 60 RPM |

---

## 4. New MCP Tool Designs

### 4.1 `grok-image-generate`

```python
Tool(
    name="grok-image-generate",
    description=(
        "Generate images from text prompts using xAI's Grok image models. "
        "Supports multiple aspect ratios, batch generation (up to 10 images), "
        "and returns either temporary URLs or base64-encoded image data. "
        "Available models: grok-imagine-image ($0.02/img), grok-imagine-image-pro ($0.07/img)."
    ),
    inputSchema={
        "type": "object",
        "properties": {
            "prompt": {
                "type": "string",
                "description": "Text description of the image to generate (e.g., 'A futuristic city skyline at sunset in watercolor style')",
            },
            "model": {
                "type": "string",
                "description": "Image model to use",
                "default": "grok-imagine-image",
                "enum": ["grok-imagine-image", "grok-imagine-image-pro", "grok-2-image-1212"],
            },
            "n": {
                "type": "integer",
                "description": "Number of images to generate (1-10)",
                "default": 1,
                "minimum": 1,
                "maximum": 10,
            },
            "aspect_ratio": {
                "type": "string",
                "description": "Aspect ratio of the generated image",
                "default": "auto",
                "enum": [
                    "1:1", "16:9", "9:16", "4:3", "3:4",
                    "3:2", "2:3", "2:1", "1:2",
                    "19.5:9", "9:19.5", "20:9", "9:20", "auto"
                ],
            },
            "response_format": {
                "type": "string",
                "description": (
                    "Output format. 'url' returns temporary download URLs. "
                    "'b64_json' returns base64-encoded image data embedded in the response."
                ),
                "default": "b64_json",
                "enum": ["url", "b64_json"],
            },
        },
        "required": ["prompt"],
    },
)
```

### 4.2 `grok-image-edit`

```python
Tool(
    name="grok-image-edit",
    description=(
        "Edit an existing image using natural language instructions. "
        "Supports style transfer, object modification, scene changes, and iterative refinement. "
        "Provide a source image via URL or base64 data URI, plus a text prompt describing the changes."
    ),
    inputSchema={
        "type": "object",
        "properties": {
            "prompt": {
                "type": "string",
                "description": "Description of the desired changes (e.g., 'Make it look like an oil painting' or 'Change the background to a beach')",
            },
            "image_url": {
                "type": "string",
                "description": (
                    "Source image to edit. Accepts: "
                    "1) A public URL (e.g., 'https://example.com/image.jpg'), or "
                    "2) A base64 data URI (e.g., 'data:image/jpeg;base64,/9j/4AAQ...')"
                ),
            },
            "model": {
                "type": "string",
                "description": "Image model to use for editing",
                "default": "grok-imagine-image",
                "enum": ["grok-imagine-image", "grok-imagine-image-pro"],
            },
            "n": {
                "type": "integer",
                "description": "Number of edited variations to generate (1-10)",
                "default": 1,
                "minimum": 1,
                "maximum": 10,
            },
            "response_format": {
                "type": "string",
                "description": "Output format: 'url' for temporary URLs, 'b64_json' for embedded base64 data",
                "default": "b64_json",
                "enum": ["url", "b64_json"],
            },
        },
        "required": ["prompt", "image_url"],
    },
)
```

### 4.3 `grok-image-models`

```python
Tool(
    name="grok-image-models",
    description=(
        "List all available xAI image and video generation models with their capabilities, "
        "pricing, rate limits, and supported features."
    ),
    inputSchema={
        "type": "object",
        "properties": {},
    },
)
```

### 4.4 `grok-video-generate`

```python
Tool(
    name="grok-video-generate",
    description=(
        "Generate videos from text prompts or images using xAI's Grok video model. "
        "Supports text-to-video, image-to-video, and video editing. "
        "Video generation is asynchronous -- this tool submits the request and polls until completion. "
        "Returns a temporary download URL for the generated MP4 video. "
        "Note: Generation may take 30-120 seconds depending on duration and resolution."
    ),
    inputSchema={
        "type": "object",
        "properties": {
            "prompt": {
                "type": "string",
                "description": "Text description of the video to generate",
            },
            "image_url": {
                "type": "string",
                "description": (
                    "Optional source image for image-to-video generation. "
                    "Accepts public URL or base64 data URI."
                ),
            },
            "video_url": {
                "type": "string",
                "description": (
                    "Optional source video URL for video editing (max 8.7s input). "
                    "When provided, duration/aspect_ratio/resolution are inherited from input."
                ),
            },
            "duration": {
                "type": "integer",
                "description": "Video duration in seconds (1-15). Not used with video_url.",
                "default": 5,
                "minimum": 1,
                "maximum": 15,
            },
            "aspect_ratio": {
                "type": "string",
                "description": "Video aspect ratio. Not used with video_url.",
                "default": "16:9",
                "enum": ["1:1", "16:9", "9:16", "4:3", "3:4", "3:2", "2:3"],
            },
            "resolution": {
                "type": "string",
                "description": "Video resolution. Higher resolution costs more and takes longer.",
                "default": "480p",
                "enum": ["480p", "720p"],
            },
        },
        "required": ["prompt"],
    },
)
```

---

## 5. Implementation Code

### 5.1 New Constants (add to top of `server.py`)

```python
# Image API Constants
XAI_IMAGE_API_BASE = "https://api.x.ai/v1/images"
XAI_VIDEO_API_BASE = "https://api.x.ai/v1/videos"

IMAGE_MODELS = [
    "grok-imagine-image",
    "grok-imagine-image-pro",
    "grok-2-image-1212",
]

VIDEO_MODELS = [
    "grok-imagine-video",
]

DEFAULT_IMAGE_MODEL = "grok-imagine-image"
DEFAULT_VIDEO_MODEL = "grok-imagine-video"

ASPECT_RATIOS_IMAGE = [
    "1:1", "16:9", "9:16", "4:3", "3:4",
    "3:2", "2:3", "2:1", "1:2",
    "19.5:9", "9:19.5", "20:9", "9:20", "auto",
]

ASPECT_RATIOS_VIDEO = [
    "1:1", "16:9", "9:16", "4:3", "3:4", "3:2", "2:3",
]

VIDEO_RESOLUTIONS = ["480p", "720p"]

# Polling config for async video generation
VIDEO_POLL_INTERVAL = 5.0  # seconds between polls
VIDEO_POLL_TIMEOUT = 300.0  # max wait time in seconds
```

### 5.2 New Import (add to imports at top of `server.py`)

```python
from mcp.types import (
    Tool,
    TextContent,
    ImageContent,  # NEW: for returning base64 images
    CallToolResult,
)
```

### 5.3 `make_image_request()` Function

```python
async def make_image_request(
    endpoint: str,
    prompt: str,
    model: str = DEFAULT_IMAGE_MODEL,
    n: int = 1,
    aspect_ratio: str = "auto",
    response_format: str = "b64_json",
    image_url: Optional[str] = None,
) -> dict | list:
    """
    Make a request to the xAI Image API.

    Args:
        endpoint: API endpoint path ("generations" or "edits")
        prompt: Text prompt describing the image
        model: Image model to use
        n: Number of images to generate (1-10)
        aspect_ratio: Aspect ratio for the generated image
        response_format: "url" for temporary URLs, "b64_json" for base64 data
        image_url: Source image URL or data URI (required for edits)

    Returns:
        API response as dictionary (single image) or list (batch)
    """
    api_key = get_api_key()

    payload: dict[str, Any] = {
        "prompt": prompt,
        "model": model,
        "n": n,
        "response_format": response_format,
    }

    # Add aspect_ratio only for generations (not always relevant for edits)
    if endpoint == "generations" and aspect_ratio:
        payload["aspect_ratio"] = aspect_ratio

    # Add image_url for edits
    if image_url:
        payload["image_url"] = image_url

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }

    url = f"{XAI_IMAGE_API_BASE}/{endpoint}"

    async with httpx.AsyncClient(timeout=300.0) as client:
        response = await client.post(
            url,
            headers=headers,
            json=payload,
        )
        response.raise_for_status()
        return response.json()
```

### 5.4 `make_video_request()` Function

```python
async def make_video_request(
    prompt: str,
    model: str = DEFAULT_VIDEO_MODEL,
    image_url: Optional[str] = None,
    video_url: Optional[str] = None,
    duration: int = 5,
    aspect_ratio: str = "16:9",
    resolution: str = "480p",
) -> dict:
    """
    Submit a video generation request and poll until completion.

    Args:
        prompt: Text prompt describing the video
        model: Video model to use
        image_url: Optional source image for image-to-video
        video_url: Optional source video for video editing
        duration: Video duration in seconds (1-15)
        aspect_ratio: Video aspect ratio
        resolution: Video resolution ("480p" or "720p")

    Returns:
        Completed video response with URL

    Raises:
        TimeoutError: If generation exceeds VIDEO_POLL_TIMEOUT
        httpx.HTTPStatusError: On API errors
    """
    api_key = get_api_key()

    # Build request payload
    payload: dict[str, Any] = {
        "model": model,
        "prompt": prompt,
    }

    if image_url:
        payload["image_url"] = image_url

    if video_url:
        payload["video_url"] = video_url
    else:
        # These params are only used for new generation, not editing
        payload["duration"] = duration
        payload["aspect_ratio"] = aspect_ratio
        payload["resolution"] = resolution

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }

    async with httpx.AsyncClient(timeout=600.0) as client:
        # Step 1: Submit the generation request
        submit_response = await client.post(
            f"{XAI_VIDEO_API_BASE}/generations",
            headers=headers,
            json=payload,
        )
        submit_response.raise_for_status()
        submit_data = submit_response.json()

        request_id = submit_data.get("request_id")
        if not request_id:
            raise ValueError(f"No request_id in video submit response: {submit_data}")

        # Step 2: Poll for completion
        elapsed = 0.0
        while elapsed < VIDEO_POLL_TIMEOUT:
            await asyncio.sleep(VIDEO_POLL_INTERVAL)
            elapsed += VIDEO_POLL_INTERVAL

            poll_response = await client.get(
                f"{XAI_VIDEO_API_BASE}/{request_id}",
                headers={
                    "Authorization": f"Bearer {api_key}",
                },
            )
            poll_response.raise_for_status()
            poll_data = poll_response.json()

            status = poll_data.get("status")

            if status == "done":
                return poll_data
            elif status == "expired":
                raise RuntimeError(
                    f"Video generation expired for request {request_id}. "
                    "The request took too long on the server side."
                )
            # status == "pending": continue polling

        raise TimeoutError(
            f"Video generation timed out after {VIDEO_POLL_TIMEOUT}s "
            f"for request {request_id}. The video may still be processing -- "
            f"you can check status at GET /v1/videos/{request_id}"
        )
```

### 5.5 `handle_image_generate()` Handler

```python
async def handle_image_generate(arguments: dict[str, Any]) -> CallToolResult:
    """Handle grok-image-generate tool invocation."""
    prompt = arguments.get("prompt")
    if not prompt:
        return CallToolResult(
            content=[TextContent(type="text", text="Error: 'prompt' is required")],
            isError=True,
        )

    model = arguments.get("model", DEFAULT_IMAGE_MODEL)
    n = arguments.get("n", 1)
    aspect_ratio = arguments.get("aspect_ratio", "auto")
    response_format = arguments.get("response_format", "b64_json")

    response = await make_image_request(
        endpoint="generations",
        prompt=prompt,
        model=model,
        n=n,
        aspect_ratio=aspect_ratio,
        response_format=response_format,
    )

    return _format_image_response(response, prompt, model, n, response_format)


def _format_image_response(
    response: dict | list,
    prompt: str,
    model: str,
    n: int,
    response_format: str,
) -> CallToolResult:
    """
    Format image API response into MCP CallToolResult.

    For b64_json: returns ImageContent objects (native MCP image support).
    For url: returns TextContent with markdown image links.
    """
    # Normalize to list
    if isinstance(response, dict):
        images = [response]
    else:
        images = response

    content = []

    # Add header text
    header = f"**Generated {len(images)} image(s)** | Model: `{model}` | Prompt: _{prompt}_\n"
    content.append(TextContent(type="text", text=header))

    for i, img_data in enumerate(images):
        moderation = img_data.get("respect_moderation", True)
        label = f"Image {i + 1}/{len(images)}" if len(images) > 1 else "Generated Image"

        if not moderation:
            content.append(TextContent(
                type="text",
                text=f"\n**{label}**: Blocked by content moderation.\n"
            ))
            continue

        if response_format == "b64_json" and "image" in img_data:
            # Return as native MCP ImageContent
            content.append(ImageContent(
                type="image",
                data=img_data["image"],
                mimeType="image/jpeg",
            ))
            content.append(TextContent(
                type="text",
                text=f"*{label} (base64 embedded)*\n"
            ))
        elif "url" in img_data:
            # Return as text with URL
            url = img_data["url"]
            content.append(TextContent(
                type="text",
                text=(
                    f"\n**{label}**\n"
                    f"URL: {url}\n"
                    f"*Note: This URL is temporary. Download the image promptly.*\n"
                ),
            ))
        else:
            # Fallback: dump raw response
            content.append(TextContent(
                type="text",
                text=f"\n**{label}**: {json.dumps(img_data, indent=2)}\n"
            ))

    return CallToolResult(content=content)
```

### 5.6 `handle_image_edit()` Handler

```python
async def handle_image_edit(arguments: dict[str, Any]) -> CallToolResult:
    """Handle grok-image-edit tool invocation."""
    prompt = arguments.get("prompt")
    image_url = arguments.get("image_url")

    if not prompt:
        return CallToolResult(
            content=[TextContent(type="text", text="Error: 'prompt' is required")],
            isError=True,
        )
    if not image_url:
        return CallToolResult(
            content=[TextContent(type="text", text="Error: 'image_url' is required")],
            isError=True,
        )

    model = arguments.get("model", DEFAULT_IMAGE_MODEL)
    n = arguments.get("n", 1)
    response_format = arguments.get("response_format", "b64_json")

    response = await make_image_request(
        endpoint="edits",
        prompt=prompt,
        model=model,
        n=n,
        response_format=response_format,
        image_url=image_url,
    )

    return _format_image_response(response, prompt, model, n, response_format)
```

### 5.7 `handle_image_models()` Handler

```python
async def handle_image_models(arguments: dict[str, Any]) -> CallToolResult:
    """Handle grok-image-models tool invocation."""
    models_info = """# Available Image & Video Models

## Image Generation Models

### grok-imagine-image
- **Type**: Image generation + editing
- **Input**: Text prompt, optional source image (for edits)
- **Price**: $0.02 per image
- **Rate Limit**: 300 requests/minute
- **Features**: Text-to-image, image editing, style transfer, batch generation (up to 10)
- **Aspect Ratios**: 1:1, 16:9, 9:16, 4:3, 3:4, 3:2, 2:3, 2:1, 1:2, 19.5:9, 9:19.5, 20:9, 9:20, auto
- **Best For**: General-purpose image generation, quick iterations, cost-effective

### grok-imagine-image-pro
- **Type**: Premium image generation
- **Input**: Text prompt, optional source image
- **Price**: $0.07 per image
- **Rate Limit**: 30 requests/minute
- **Features**: Higher quality output, better prompt adherence, more detailed images
- **Best For**: Production-quality images, marketing materials, detailed art

### grok-2-image-1212
- **Type**: Legacy text-to-image
- **Input**: Text prompt only
- **Price**: $0.07 per image
- **Rate Limit**: 300 requests/minute
- **Features**: Text-to-image generation only (no editing support)
- **Best For**: Backward compatibility, specific style preferences

## Video Generation Models

### grok-imagine-video
- **Type**: Video generation (async)
- **Input**: Text prompt, optional source image/video
- **Price**: $0.05 per second of generated video
- **Rate Limit**: 60 requests/minute
- **Features**: Text-to-video, image-to-video, video editing
- **Duration**: 1-15 seconds (generation), max 8.7s input (editing)
- **Resolutions**: 480p, 720p
- **Aspect Ratios**: 1:1, 16:9, 9:16, 4:3, 3:4, 3:2, 2:3
- **Best For**: Short video clips, animations, product demos

## Output Formats

- **url**: Returns temporary download URL (expires quickly -- download immediately)
- **b64_json**: Returns base64-encoded JPEG data (embedded in response, no expiry)

## Content Moderation

All generated images/videos pass through content moderation. Check the `respect_moderation` field:
- `true`: Content passed moderation and was generated
- `false`: Content was blocked by moderation filters
"""

    return CallToolResult(
        content=[TextContent(type="text", text=models_info)],
    )
```

### 5.8 `handle_video_generate()` Handler

```python
async def handle_video_generate(arguments: dict[str, Any]) -> CallToolResult:
    """Handle grok-video-generate tool invocation."""
    prompt = arguments.get("prompt")
    if not prompt:
        return CallToolResult(
            content=[TextContent(type="text", text="Error: 'prompt' is required")],
            isError=True,
        )

    image_url = arguments.get("image_url")
    video_url = arguments.get("video_url")
    duration = arguments.get("duration", 5)
    aspect_ratio = arguments.get("aspect_ratio", "16:9")
    resolution = arguments.get("resolution", "480p")

    # Determine generation type for user feedback
    if video_url:
        gen_type = "video editing"
    elif image_url:
        gen_type = "image-to-video"
    else:
        gen_type = "text-to-video"

    try:
        response = await make_video_request(
            prompt=prompt,
            model=DEFAULT_VIDEO_MODEL,
            image_url=image_url,
            video_url=video_url,
            duration=duration,
            aspect_ratio=aspect_ratio,
            resolution=resolution,
        )
    except TimeoutError as e:
        return CallToolResult(
            content=[TextContent(
                type="text",
                text=f"**Video generation timed out**\n\n{str(e)}\n\n"
                     "The video may still be processing on the server. "
                     "You can try again later or increase the timeout."
            )],
            isError=True,
        )
    except RuntimeError as e:
        return CallToolResult(
            content=[TextContent(type="text", text=f"**Video generation failed**: {str(e)}")],
            isError=True,
        )

    # Extract video info from response
    video_data = response.get("video", {})
    video_url_result = video_data.get("url", "")
    video_duration = video_data.get("duration", "unknown")
    moderation = video_data.get("respect_moderation", True)

    if not moderation:
        return CallToolResult(
            content=[TextContent(
                type="text",
                text="**Video blocked by content moderation.**\n\nThe generated video did not pass moderation filters."
            )],
        )

    result_text = f"""# Video Generated Successfully

**Type**: {gen_type}
**Model**: {DEFAULT_VIDEO_MODEL}
**Prompt**: _{prompt}_
**Duration**: {video_duration} seconds
**Resolution**: {resolution}

## Download URL

{video_url_result}

**IMPORTANT**: This URL is temporary. Download the video immediately.

## Details
- Format: MP4
- The URL will expire shortly after generation
- Content moderation: Passed
"""

    return CallToolResult(
        content=[TextContent(type="text", text=result_text)],
    )
```

### 5.9 Updated `list_tools()` -- New Tool Entries to Add

Add these 4 Tool entries to the return list in `list_tools()`, after the existing tools and before the closing bracket:

```python
        # Image & Video Generation Tools
        Tool(
            name="grok-image-generate",
            description=(
                "Generate images from text prompts using xAI's Grok image models. "
                "Supports multiple aspect ratios, batch generation (up to 10 images), "
                "and returns either temporary URLs or base64-encoded image data. "
                "Available models: grok-imagine-image ($0.02/img), grok-imagine-image-pro ($0.07/img)."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "Text description of the image to generate (e.g., 'A futuristic city skyline at sunset in watercolor style')",
                    },
                    "model": {
                        "type": "string",
                        "description": "Image model to use",
                        "default": "grok-imagine-image",
                        "enum": IMAGE_MODELS,
                    },
                    "n": {
                        "type": "integer",
                        "description": "Number of images to generate (1-10)",
                        "default": 1,
                        "minimum": 1,
                        "maximum": 10,
                    },
                    "aspect_ratio": {
                        "type": "string",
                        "description": "Aspect ratio of the generated image",
                        "default": "auto",
                        "enum": ASPECT_RATIOS_IMAGE,
                    },
                    "response_format": {
                        "type": "string",
                        "description": (
                            "Output format. 'url' returns temporary download URLs. "
                            "'b64_json' returns base64-encoded image data embedded in the response."
                        ),
                        "default": "b64_json",
                        "enum": ["url", "b64_json"],
                    },
                },
                "required": ["prompt"],
            },
        ),
        Tool(
            name="grok-image-edit",
            description=(
                "Edit an existing image using natural language instructions. "
                "Supports style transfer, object modification, scene changes, and iterative refinement. "
                "Provide a source image via URL or base64 data URI, plus a text prompt describing the changes."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "Description of the desired changes (e.g., 'Make it look like an oil painting' or 'Change the background to a beach')",
                    },
                    "image_url": {
                        "type": "string",
                        "description": (
                            "Source image to edit. Accepts: "
                            "1) A public URL (e.g., 'https://example.com/image.jpg'), or "
                            "2) A base64 data URI (e.g., 'data:image/jpeg;base64,/9j/4AAQ...')"
                        ),
                    },
                    "model": {
                        "type": "string",
                        "description": "Image model to use for editing",
                        "default": "grok-imagine-image",
                        "enum": ["grok-imagine-image", "grok-imagine-image-pro"],
                    },
                    "n": {
                        "type": "integer",
                        "description": "Number of edited variations to generate (1-10)",
                        "default": 1,
                        "minimum": 1,
                        "maximum": 10,
                    },
                    "response_format": {
                        "type": "string",
                        "description": "Output format: 'url' for temporary URLs, 'b64_json' for embedded base64 data",
                        "default": "b64_json",
                        "enum": ["url", "b64_json"],
                    },
                },
                "required": ["prompt", "image_url"],
            },
        ),
        Tool(
            name="grok-image-models",
            description=(
                "List all available xAI image and video generation models with their capabilities, "
                "pricing, rate limits, and supported features."
            ),
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        Tool(
            name="grok-video-generate",
            description=(
                "Generate videos from text prompts or images using xAI's Grok video model. "
                "Supports text-to-video, image-to-video, and video editing. "
                "Video generation is asynchronous -- this tool submits the request and polls until completion. "
                "Returns a temporary download URL for the generated MP4 video. "
                "Note: Generation may take 30-120 seconds depending on duration and resolution."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "Text description of the video to generate",
                    },
                    "image_url": {
                        "type": "string",
                        "description": (
                            "Optional source image for image-to-video generation. "
                            "Accepts public URL or base64 data URI."
                        ),
                    },
                    "video_url": {
                        "type": "string",
                        "description": (
                            "Optional source video URL for video editing (max 8.7s input). "
                            "When provided, duration/aspect_ratio/resolution are inherited from input."
                        ),
                    },
                    "duration": {
                        "type": "integer",
                        "description": "Video duration in seconds (1-15). Not used with video_url.",
                        "default": 5,
                        "minimum": 1,
                        "maximum": 15,
                    },
                    "aspect_ratio": {
                        "type": "string",
                        "description": "Video aspect ratio. Not used with video_url.",
                        "default": "16:9",
                        "enum": ASPECT_RATIOS_VIDEO,
                    },
                    "resolution": {
                        "type": "string",
                        "description": "Video resolution. Higher resolution costs more and takes longer.",
                        "default": "480p",
                        "enum": VIDEO_RESOLUTIONS,
                    },
                },
                "required": ["prompt"],
            },
        ),
```

### 5.10 Updated `call_tool()` Dispatcher

Add these cases to the `call_tool()` function, in the `try` block, after the chain tools and before the `else` (unknown tool):

```python
        # Image & Video generation tools
        elif name == "grok-image-generate":
            return await handle_image_generate(arguments)
        elif name == "grok-image-edit":
            return await handle_image_edit(arguments)
        elif name == "grok-image-models":
            return await handle_image_models(arguments)
        elif name == "grok-video-generate":
            return await handle_video_generate(arguments)
```

---

## 6. Updated Constants & Models

### 6.1 Updated `AVAILABLE_MODELS` (Text Models)

Expand the existing list to include all current text models:

```python
AVAILABLE_MODELS = [
    "grok-4",
    "grok-4-1-fast",
    "grok-4-1-fast-reasoning",
    "grok-4-1-fast-non-reasoning",
    "grok-4-fast-reasoning",
    "grok-4-fast-non-reasoning",
    "grok-4-0709",
    "grok-code-fast-1",
    "grok-3",
    "grok-3-fast",
    "grok-3-mini",
    "grok-2",
    "grok-2-latest",
    "grok-2-vision-1212",
]
```

### 6.2 Updated `handle_grok_models()`

The existing `handle_grok_models()` should be updated to reflect all text models. Here is the updated info string:

```python
async def handle_grok_models(arguments: dict[str, Any]) -> CallToolResult:
    """Handle grok-models tool invocation."""
    models_info = """# Available Grok Text Models

## Flagship Models

### grok-4
- **Context**: 256K tokens
- **Input**: Text + Image
- **Capabilities**: Reasoning, Function Calling, Structured Output
- **Pricing**: $3.00/$15.00 per 1M tokens (in/out)

### grok-4-1-fast
- **Context**: 2M tokens
- **Input**: Text + Image
- **Capabilities**: Function Calling, Structured Output
- **Pricing**: $0.20/$0.50 per 1M tokens (in/out)
- **Speed**: Fast

### grok-4-1-fast-reasoning
- **Context**: 2M tokens
- **Input**: Text + Image
- **Capabilities**: Reasoning, Function Calling, Structured Output
- **Pricing**: $0.20/$0.50 per 1M tokens (in/out)

### grok-4-0709
- **Context**: 256K tokens
- **Input**: Text + Image
- **Capabilities**: Reasoning, Function Calling, Structured Output
- **Pricing**: $3.00/$15.00 per 1M tokens (in/out)

## Specialized Models

### grok-code-fast-1
- **Context**: 256K tokens
- **Input**: Text only
- **Capabilities**: Reasoning, Function Calling, Structured Output
- **Pricing**: $0.20/$1.50 per 1M tokens (in/out)
- **Best For**: Code generation and analysis

## Previous Generation

### grok-3
- **Context**: 131K tokens | **Pricing**: $3.00/$15.00

### grok-3-fast
- **Context**: 131K tokens | **Pricing**: $3.00/$15.00

### grok-3-mini
- **Context**: 131K tokens | **Pricing**: $0.30/$0.50 | Reasoning capable

### grok-2 / grok-2-latest
- **Context**: 32K tokens | **Pricing**: $2.00/$10.00

### grok-2-vision-1212
- **Context**: 32K tokens | **Input**: Text + Image | **Pricing**: $2.00/$10.00

## Tool Capabilities

All models support web search and X search via the Responses API.
For image/video models, use `grok-image-models` tool.
"""

    return CallToolResult(
        content=[TextContent(type="text", text=models_info)],
    )
```

### 6.3 Version Bump in `__init__.py`

```python
__version__ = "2.0.0"
```

### 6.4 Updated `pyproject.toml` Description

```toml
version = "2.0.0"
description = "MCP Server for xAI Grok API - Chat, Web Search, X Search, Image Generation, Video Generation"
keywords = ["mcp", "grok", "xai", "ai", "search", "twitter", "x", "image-generation", "video-generation"]
```

---

## 7. MCP Response Strategy (Images via MCP)

### Decision: Dual-Format Response

The implementation supports **both** response formats, with `b64_json` as default:

| Format | MCP Content Type | Pros | Cons |
|--------|-----------------|------|------|
| `b64_json` (default) | `ImageContent` | Native MCP image rendering, no expiry, works offline | Larger response payload, ~1.3MB per image |
| `url` | `TextContent` with URL | Small payload, fast response | URLs expire quickly, requires network |

### Why `b64_json` is the Default

1. **MCP ImageContent Support** -- The MCP specification (2025-11-25) natively supports `ImageContent` with `type: "image"`, `data: <base64>`, `mimeType: "image/jpeg"`. Claude Code and other MCP clients can render these inline.

2. **No URL Expiry Risk** -- xAI image URLs are temporary. By the time a user acts on the response, the URL may have expired. Base64 data is permanent in the conversation.

3. **Offline Capability** -- Base64 images work even if the network drops after generation.

### Implementation Detail

The `_format_image_response()` helper function handles both formats:
- For `b64_json`: Creates `ImageContent(type="image", data=..., mimeType="image/jpeg")` objects
- For `url`: Creates `TextContent` with markdown-formatted URLs and download warnings

### Import Required

The `ImageContent` class must be imported from `mcp.types`. Verify the installed `mcp` package version supports this. If not available (older SDK), fall back to `TextContent` with base64 data URI:

```python
# Fallback if ImageContent is not available in the installed mcp version
try:
    from mcp.types import ImageContent
    HAS_IMAGE_CONTENT = True
except ImportError:
    HAS_IMAGE_CONTENT = False

# In _format_image_response():
if HAS_IMAGE_CONTENT:
    content.append(ImageContent(
        type="image",
        data=img_data["image"],
        mimeType="image/jpeg",
    ))
else:
    # Fallback: return as text with data URI
    content.append(TextContent(
        type="text",
        text=f"![{label}](data:image/jpeg;base64,{img_data['image'][:50]}...)\n"
             f"*Base64 image data ({len(img_data['image'])} chars)*\n"
    ))
```

---

## 8. Testing Strategy

### 8.1 Unit Tests (No API calls)

Create `tests/test_image_tools.py`:

```python
"""Tests for image and video generation tools."""
import pytest
import json
from unittest.mock import AsyncMock, patch, MagicMock
from mcp.types import TextContent, CallToolResult

# Test imports
from grok_mcp_server.server import (
    handle_image_generate,
    handle_image_edit,
    handle_image_models,
    handle_video_generate,
    _format_image_response,
    make_image_request,
    make_video_request,
)


class TestImageGenerate:
    """Tests for grok-image-generate handler."""

    @pytest.mark.asyncio
    async def test_missing_prompt_returns_error(self):
        result = await handle_image_generate({})
        assert result.isError is True
        assert "prompt" in result.content[0].text.lower()

    @pytest.mark.asyncio
    @patch("grok_mcp_server.server.make_image_request")
    async def test_basic_generation_url_format(self, mock_request):
        mock_request.return_value = {
            "url": "https://example.com/image.jpg",
            "model": "grok-imagine-image",
            "respect_moderation": True,
        }
        result = await handle_image_generate({
            "prompt": "A cat",
            "response_format": "url",
        })
        assert not result.isError
        assert any("https://example.com/image.jpg" in c.text for c in result.content if hasattr(c, "text"))
        mock_request.assert_called_once()

    @pytest.mark.asyncio
    @patch("grok_mcp_server.server.make_image_request")
    async def test_basic_generation_b64_format(self, mock_request):
        mock_request.return_value = {
            "image": "iVBORw0KGgoAAAANSUhEUg==",
            "model": "grok-imagine-image",
            "respect_moderation": True,
        }
        result = await handle_image_generate({
            "prompt": "A cat",
            "response_format": "b64_json",
        })
        assert not result.isError
        # Should contain ImageContent
        image_contents = [c for c in result.content if getattr(c, "type", "") == "image"]
        assert len(image_contents) >= 1

    @pytest.mark.asyncio
    @patch("grok_mcp_server.server.make_image_request")
    async def test_batch_generation(self, mock_request):
        mock_request.return_value = [
            {"url": "https://example.com/1.jpg", "model": "grok-imagine-image", "respect_moderation": True},
            {"url": "https://example.com/2.jpg", "model": "grok-imagine-image", "respect_moderation": True},
            {"url": "https://example.com/3.jpg", "model": "grok-imagine-image", "respect_moderation": True},
        ]
        result = await handle_image_generate({
            "prompt": "A cat",
            "n": 3,
            "response_format": "url",
        })
        assert not result.isError
        full_text = " ".join(c.text for c in result.content if hasattr(c, "text"))
        assert "3 image(s)" in full_text

    @pytest.mark.asyncio
    @patch("grok_mcp_server.server.make_image_request")
    async def test_moderation_blocked(self, mock_request):
        mock_request.return_value = {
            "url": "",
            "model": "grok-imagine-image",
            "respect_moderation": False,
        }
        result = await handle_image_generate({
            "prompt": "something",
            "response_format": "url",
        })
        full_text = " ".join(c.text for c in result.content if hasattr(c, "text"))
        assert "moderation" in full_text.lower()

    @pytest.mark.asyncio
    @patch("grok_mcp_server.server.make_image_request")
    async def test_custom_model_and_aspect_ratio(self, mock_request):
        mock_request.return_value = {
            "url": "https://example.com/image.jpg",
            "model": "grok-imagine-image-pro",
            "respect_moderation": True,
        }
        await handle_image_generate({
            "prompt": "A cat",
            "model": "grok-imagine-image-pro",
            "aspect_ratio": "16:9",
            "response_format": "url",
        })
        call_kwargs = mock_request.call_args
        assert call_kwargs[1]["model"] == "grok-imagine-image-pro" or call_kwargs.kwargs.get("model") == "grok-imagine-image-pro"


class TestImageEdit:
    """Tests for grok-image-edit handler."""

    @pytest.mark.asyncio
    async def test_missing_prompt_returns_error(self):
        result = await handle_image_edit({"image_url": "https://example.com/img.jpg"})
        assert result.isError is True

    @pytest.mark.asyncio
    async def test_missing_image_url_returns_error(self):
        result = await handle_image_edit({"prompt": "Make it blue"})
        assert result.isError is True

    @pytest.mark.asyncio
    @patch("grok_mcp_server.server.make_image_request")
    async def test_basic_edit(self, mock_request):
        mock_request.return_value = {
            "url": "https://example.com/edited.jpg",
            "model": "grok-imagine-image",
            "respect_moderation": True,
        }
        result = await handle_image_edit({
            "prompt": "Make it an oil painting",
            "image_url": "https://example.com/source.jpg",
            "response_format": "url",
        })
        assert not result.isError
        mock_request.assert_called_once_with(
            endpoint="edits",
            prompt="Make it an oil painting",
            model="grok-imagine-image",
            n=1,
            response_format="url",
            image_url="https://example.com/source.jpg",
        )


class TestImageModels:
    """Tests for grok-image-models handler."""

    @pytest.mark.asyncio
    async def test_returns_model_info(self):
        result = await handle_image_models({})
        assert not result.isError
        text = result.content[0].text
        assert "grok-imagine-image" in text
        assert "grok-imagine-image-pro" in text
        assert "grok-imagine-video" in text
        assert "$0.02" in text


class TestVideoGenerate:
    """Tests for grok-video-generate handler."""

    @pytest.mark.asyncio
    async def test_missing_prompt_returns_error(self):
        result = await handle_video_generate({})
        assert result.isError is True

    @pytest.mark.asyncio
    @patch("grok_mcp_server.server.make_video_request")
    async def test_basic_text_to_video(self, mock_request):
        mock_request.return_value = {
            "status": "done",
            "video": {
                "url": "https://vidgen.x.ai/video.mp4",
                "duration": 5,
                "respect_moderation": True,
            },
            "model": "grok-imagine-video",
        }
        result = await handle_video_generate({
            "prompt": "A rocket launching",
            "duration": 5,
        })
        assert not result.isError
        full_text = " ".join(c.text for c in result.content if hasattr(c, "text"))
        assert "video.mp4" in full_text
        assert "text-to-video" in full_text

    @pytest.mark.asyncio
    @patch("grok_mcp_server.server.make_video_request")
    async def test_timeout_returns_error(self, mock_request):
        mock_request.side_effect = TimeoutError("Timed out")
        result = await handle_video_generate({"prompt": "Something"})
        assert result.isError is True
        assert "timed out" in result.content[0].text.lower()

    @pytest.mark.asyncio
    @patch("grok_mcp_server.server.make_video_request")
    async def test_video_moderation_blocked(self, mock_request):
        mock_request.return_value = {
            "status": "done",
            "video": {
                "url": "",
                "duration": 0,
                "respect_moderation": False,
            },
            "model": "grok-imagine-video",
        }
        result = await handle_video_generate({"prompt": "Something"})
        full_text = " ".join(c.text for c in result.content if hasattr(c, "text"))
        assert "moderation" in full_text.lower()


class TestMakeImageRequest:
    """Tests for the make_image_request function."""

    @pytest.mark.asyncio
    @patch("grok_mcp_server.server.get_api_key", return_value="test-key")
    @patch("httpx.AsyncClient.post")
    async def test_generations_payload(self, mock_post, mock_key):
        mock_response = MagicMock()
        mock_response.json.return_value = {"url": "https://example.com/img.jpg"}
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        await make_image_request(
            endpoint="generations",
            prompt="A cat",
            model="grok-imagine-image",
            n=2,
            aspect_ratio="16:9",
            response_format="url",
        )

        call_args = mock_post.call_args
        payload = call_args.kwargs.get("json") or call_args[1].get("json")
        assert payload["prompt"] == "A cat"
        assert payload["model"] == "grok-imagine-image"
        assert payload["n"] == 2
        assert payload["aspect_ratio"] == "16:9"
        assert payload["response_format"] == "url"

    @pytest.mark.asyncio
    @patch("grok_mcp_server.server.get_api_key", return_value="test-key")
    @patch("httpx.AsyncClient.post")
    async def test_edits_payload_includes_image_url(self, mock_post, mock_key):
        mock_response = MagicMock()
        mock_response.json.return_value = {"url": "https://example.com/edited.jpg"}
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        await make_image_request(
            endpoint="edits",
            prompt="Style transfer",
            image_url="https://example.com/source.jpg",
        )

        call_args = mock_post.call_args
        payload = call_args.kwargs.get("json") or call_args[1].get("json")
        assert payload["image_url"] == "https://example.com/source.jpg"
        assert "aspect_ratio" not in payload  # Not added for edits


class TestFormatImageResponse:
    """Tests for the _format_image_response helper."""

    def test_single_url_response(self):
        response = {
            "url": "https://example.com/image.jpg",
            "model": "grok-imagine-image",
            "respect_moderation": True,
        }
        result = _format_image_response(response, "A cat", "grok-imagine-image", 1, "url")
        texts = [c.text for c in result.content if hasattr(c, "text")]
        assert any("https://example.com/image.jpg" in t for t in texts)

    def test_batch_url_response(self):
        response = [
            {"url": "https://example.com/1.jpg", "model": "grok-imagine-image", "respect_moderation": True},
            {"url": "https://example.com/2.jpg", "model": "grok-imagine-image", "respect_moderation": True},
        ]
        result = _format_image_response(response, "Cats", "grok-imagine-image", 2, "url")
        texts = " ".join(c.text for c in result.content if hasattr(c, "text"))
        assert "2 image(s)" in texts
        assert "Image 1/2" in texts
        assert "Image 2/2" in texts
```

### 8.2 Integration Tests (Requires API key)

Create `tests/test_image_integration.py`:

```python
"""Integration tests for image generation (requires XAI_API_KEY)."""
import os
import pytest

pytestmark = pytest.mark.skipif(
    not os.environ.get("XAI_API_KEY"),
    reason="XAI_API_KEY not set"
)


class TestImageGenerationIntegration:

    @pytest.mark.asyncio
    async def test_generate_single_image_url(self):
        from grok_mcp_server.server import handle_image_generate
        result = await handle_image_generate({
            "prompt": "A simple red circle on white background",
            "model": "grok-imagine-image",
            "n": 1,
            "response_format": "url",
        })
        assert not result.isError
        texts = " ".join(c.text for c in result.content if hasattr(c, "text"))
        assert "http" in texts

    @pytest.mark.asyncio
    async def test_generate_single_image_base64(self):
        from grok_mcp_server.server import handle_image_generate
        result = await handle_image_generate({
            "prompt": "A blue square",
            "model": "grok-imagine-image",
            "n": 1,
            "response_format": "b64_json",
        })
        assert not result.isError
        image_contents = [c for c in result.content if getattr(c, "type", "") == "image"]
        assert len(image_contents) >= 1

    @pytest.mark.asyncio
    async def test_image_models_returns_info(self):
        from grok_mcp_server.server import handle_image_models
        result = await handle_image_models({})
        assert not result.isError
        assert "grok-imagine-image" in result.content[0].text
```

### 8.3 Test Execution Commands

```bash
# Unit tests only (no API key needed)
pytest tests/test_image_tools.py -v

# Integration tests (requires XAI_API_KEY)
XAI_API_KEY=REDACTED

# All tests
pytest tests/ -v
```

---

## 9. Configuration & Environment Changes

### 9.1 No New Environment Variables

The image and video APIs use the same `XAI_API_KEY` as the text API. No additional env vars needed.

### 9.2 Updated `.env.example`

No changes needed -- `XAI_API_KEY` is already documented.

### 9.3 No New Dependencies

The implementation uses only `httpx` (already a dependency) and `asyncio` (stdlib). No new packages required.

### 9.4 MCP Client Configuration

No changes needed to `claude_desktop_config.json` or similar MCP client configs. The new tools auto-register through the existing server.

---

## 10. Migration Checklist

### Pre-Implementation

- [ ] Read this plan fully
- [ ] Verify `mcp` package supports `ImageContent` (check `from mcp.types import ImageContent`)
- [ ] If `ImageContent` not available, use the fallback pattern from Section 7

### Implementation Steps (in order)

1. [ ] **Add new constants** (Section 5.1) to top of `server.py` after existing constants
2. [ ] **Update imports** (Section 5.2) -- add `ImageContent` to imports
3. [ ] **Add `make_image_request()` function** (Section 5.3) after `make_grok_request()`
4. [ ] **Add `make_video_request()` function** (Section 5.4) after `make_image_request()`
5. [ ] **Add `_format_image_response()` helper** (Section 5.5) after `extract_response_text()`
6. [ ] **Add `handle_image_generate()` handler** (Section 5.5)
7. [ ] **Add `handle_image_edit()` handler** (Section 5.6)
8. [ ] **Add `handle_image_models()` handler** (Section 5.7)
9. [ ] **Add `handle_video_generate()` handler** (Section 5.8)
10. [ ] **Add 4 new Tool entries** to `list_tools()` (Section 5.9)
11. [ ] **Add 4 new dispatcher cases** to `call_tool()` (Section 5.10)
12. [ ] **Update `AVAILABLE_MODELS`** list (Section 6.1)
13. [ ] **Update `handle_grok_models()`** content (Section 6.2)
14. [ ] **Bump version** in `__init__.py` to `2.0.0` (Section 6.3)
15. [ ] **Update `pyproject.toml`** description and version (Section 6.4)

### Post-Implementation

16. [ ] Create `tests/test_image_tools.py` (Section 8.1)
17. [ ] Run unit tests: `pytest tests/test_image_tools.py -v`
18. [ ] Run integration test with live API key (Section 8.2)
19. [ ] Test from Claude Code: invoke `grok-image-generate` tool
20. [ ] Update `GROK-DEV-CONTEXT.md` with new tool inventory
21. [ ] Update README.md with new tools documentation

### Verification

22. [ ] Confirm 16 tools appear in `grok-models` (or tool list)
23. [ ] Confirm image generation returns viewable images
24. [ ] Confirm image editing works with URL and base64 input
25. [ ] Confirm video generation polls correctly and returns MP4 URL
26. [ ] Confirm error handling for missing prompts, API failures, timeouts, moderation blocks

---

## Appendix A: Complete Diff Summary

### Files Modified

| File | Lines Added (approx) | Description |
|------|---------------------|-------------|
| `server.py` | ~350 | Constants, 2 request functions, 5 handlers, 4 tool defs, 4 dispatcher cases |
| `__init__.py` | 1 | Version bump |
| `pyproject.toml` | 2 | Version + description |

### Files Created

| File | Lines (approx) | Description |
|------|---------------|-------------|
| `tests/test_image_tools.py` | ~250 | Unit tests for all new tools |
| `tests/test_image_integration.py` | ~50 | Integration tests (optional) |

### Total New Code: ~650 lines

---

## Appendix B: Response Format Decision Matrix

| Scenario | Recommended Format | Reason |
|----------|-------------------|--------|
| User wants to see image inline | `b64_json` | MCP ImageContent renders inline |
| User wants to download/save image | `url` | Direct download link |
| Slow network / large batch | `url` | Smaller payload |
| Chained workflows (generate -> edit) | `b64_json` | Image data stays in context |
| Debugging / logging | `url` | Easier to inspect |

---

*End of Implementation Plan*
