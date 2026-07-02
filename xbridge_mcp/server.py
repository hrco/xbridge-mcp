#!/usr/bin/env python3
"""
xBridge MCP - xAI Grok API Integration

Provides MCP tools for interacting with xAI's Grok API including:
- Chat completions with various Grok models
- Web search with domain filtering
- X (Twitter) search with handle and date filtering
- Session management for persistent conversation history
- Tool chaining for multi-step workflows (search → summarize, research, debug)
- Image and video generation
"""

import os
import sys
import json
import httpx
import base64
import asyncio
from pathlib import Path
from typing import Optional, Any
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    Tool,
    TextContent,
    ImageContent,
    AudioContent,
    CallToolResult,
)

# Import session management and tool chaining
from .session_manager import get_session_manager
from .tool_chains import ChainBuilder
from .token_counter import count_messages_tokens, usage_tracker
from .tokenizer import validate_key, check_free_limit
# Constants — regional endpoint via XAI_REGION env var (e.g. "us-east-1")
_XAI_REGION = os.environ.get("XAI_REGION", "")
_XAI_HOST = f"https://{_XAI_REGION}.api.x.ai" if _XAI_REGION else "https://api.x.ai"
XAI_API_BASE = f"{_XAI_HOST}/v1/responses"
DEFAULT_MODEL = "grok-4-1-fast"
AVAILABLE_MODELS = [
    # grok-4.20 family (1M context, reasoning + multi-agent)
    "grok-4.20-0309-reasoning",
    "grok-4.20-0309-non-reasoning",
    "grok-4.20-multi-agent-0309",
    # grok-4.3 — flagship (1M context, May 2026)
    "grok-4.3",
    # grok-build-0.1 — coding-focused, replaces retired grok-code-fast-1
    "grok-build-0.1",
    # grok-4.1 family — legacy slugs, retirement status vs May-15-2026 list unconfirmed
    "grok-4",
    "grok-4-1-fast",
    # Previous generation — legacy slugs, retirement status vs May-15-2026 list unconfirmed
    "grok-3-fast",
    "grok-3-mini",
    "grok-2",
    "grok-2-latest",
    "grok-2-vision-1212",
]

# Image & Video API Constants (also respect regional endpoint)
XAI_IMAGE_API_BASE = f"{_XAI_HOST}/v1/images"
XAI_VIDEO_API_BASE = f"{_XAI_HOST}/v1/videos"
XAI_DOCS_MCP_URL = "https://docs.x.ai/api/mcp"

IMAGE_MODELS = [
    "grok-imagine-image",
    "grok-imagine-image-quality",
    # legacy - no current doc presence, retirement status unconfirmed
    "grok-2-image-1212",
]

VIDEO_MODELS = [
    "grok-imagine-video",
    "grok-imagine-video-1.5",
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

VIDEO_RESOLUTIONS = ["480p", "720p", "1080p"]

# 1080p is only supported on grok-imagine-video-1.5, and only for image-to-video
# generation (not text-to-video, not video editing). Naively adding it to
# VIDEO_RESOLUTIONS without gating would let callers request combos xAI 400s on.
VIDEO_1080P_MODEL = "grok-imagine-video-1.5"

# Polling config for async video generation
VIDEO_POLL_INTERVAL = 5.0  # seconds between polls
VIDEO_POLL_TIMEOUT = 600.0  # max wait time in seconds

# Text-to-Speech API Constants (also respects regional endpoint)
TTS_API_BASE = f"{_XAI_HOST}/v1/tts"
TTS_VOICES = ["eve", "ara", "rex", "sal", "leo"]
DEFAULT_TTS_VOICE = "eve"

# Initialize MCP Server
server = Server("xbridge-mcp")

# ---------------------------------------------------------------------------
# Shared HTTP client — reuses connection pool across all make_grok_request()
# calls instead of creating a new client per invocation.  Image/video requests
# keep their own per-call clients because they carry different timeouts.
# ---------------------------------------------------------------------------
_grok_client: Optional[httpx.AsyncClient] = None


def _get_grok_client() -> httpx.AsyncClient:
    """Return (or lazily create) the module-level Grok API client."""
    global _grok_client
    if _grok_client is None or _grok_client.is_closed:
        _grok_client = httpx.AsyncClient(timeout=300.0)
    return _grok_client


def get_api_key() -> str:
    """Retrieve xAI API key from environment."""
    api_key = os.environ.get("XAI_API_KEY")
    if not api_key:
        raise ValueError(
            "XAI_API_KEY environment variable is not set. "
            "Please set it with your xAI API key from https://x.ai/api"
        )
    return api_key


async def make_grok_request(
    messages: list[dict],
    model: str = DEFAULT_MODEL,
    tools: Optional[list[dict]] = None,
    system_prompt: Optional[str] = None,
    service_tier: Optional[str] = None,
) -> dict:
    """
    Make a request to the xAI Grok API.

    Args:
        messages: List of message objects with role and content
        model: Grok model to use
        tools: Optional list of tool configurations
        system_prompt: Optional system prompt to prepend
        service_tier: Optional priority processing tier ("default" or "priority").
            Priority is opportunistic (2x price premium, not a reservation) - xAI
            only bills for it if the response confirms service_tier == "priority".

    Returns:
        API response as dictionary
    """
    api_key = get_api_key()

    # Build input messages
    input_messages = []

    # Add system prompt if provided
    if system_prompt:
        input_messages.append({
            "role": "system",
            "content": system_prompt
        })

    # Add user messages
    input_messages.extend(messages)

    # Build request payload
    payload = {
        "model": model,
        "input": input_messages,
    }

    # Add tools if specified
    if tools:
        payload["tools"] = tools

    if service_tier:
        payload["service_tier"] = service_tier

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }

    client = _get_grok_client()
    response = await client.post(
        XAI_API_BASE,
        headers=headers,
        json=payload,
    )
    response.raise_for_status()
    result = response.json()

    # Track usage for billing/quotas
    try:
        prompt_tokens = count_messages_tokens(input_messages)
        completion_tokens = 0
        if 'output' in result:
            completion_tokens = count_messages_tokens(result.get('output', []))
        usage_tracker.record_usage(
            api_key=api_key,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            tool_name='grok-chat'
        )
    except Exception:
        pass

    return result


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
        result = response.json()

        # xAI API wraps responses in {"data": [...]}, unwrap it
        if isinstance(result, dict) and "data" in result:
            data = result["data"]
            return data[0] if len(data) == 1 else data

        return result


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
        resolution: Video resolution ("480p", "720p", or "1080p" -- 1080p is only
            supported on grok-imagine-video-1.5 for image-to-video generation)

    Returns:
        Completed video response with URL

    Raises:
        TimeoutError: If generation exceeds VIDEO_POLL_TIMEOUT
        RuntimeError: If the request expires or fails server-side
        httpx.HTTPStatusError: On API errors
    """
    api_key = get_api_key()

    payload: dict[str, Any] = {
        "model": model,
        "prompt": prompt,
    }

    if image_url:
        payload["image_url"] = image_url

    if video_url:
        payload["video_url"] = video_url
    else:
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

            if status == "done" or "video" in poll_data:
                return poll_data
            elif status == "expired":
                raise RuntimeError(
                    f"Video generation expired for request {request_id}. "
                    "The request took too long on the server side."
                )
            elif status == "failed" or poll_data.get("error"):
                error = poll_data.get("error") or {}
                code = error.get("code", "unknown")
                message = error.get("message", "no error details provided")
                raise RuntimeError(
                    f"Video generation failed for request {request_id} "
                    f"(code: {code}): {message}"
                )

        raise TimeoutError(
            f"Video generation timed out after {VIDEO_POLL_TIMEOUT}s "
            f"for request {request_id}."
        )


async def make_tts_request(
    text: str,
    voice_id: str = DEFAULT_TTS_VOICE,
    language: str = "auto",
    speed: float = 1.0,
) -> dict:
    """
    Make a request to the xAI Text-to-Speech API.

    Always requests `with_timestamps: true` regardless of what the caller wants
    surfaced, so the API always returns the JSON (base64 audio) response shape
    instead of sometimes returning raw binary -- keeps one response-parsing
    path instead of branching on content-type.

    Args:
        text: Text to synthesize (max 15,000 chars)
        voice_id: Voice to use (see TTS_VOICES)
        language: BCP-47 language code or "auto"
        speed: Speech speed (0.7-1.5)

    Returns:
        API response dict: {"audio", "content_type", "duration", "audio_timestamps"}
    """
    api_key = get_api_key()

    payload: dict[str, Any] = {
        "text": text,
        "voice_id": voice_id,
        "language": language,
        "speed": speed,
        "with_timestamps": True,
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }

    async with httpx.AsyncClient(timeout=300.0) as client:
        response = await client.post(
            TTS_API_BASE,
            headers=headers,
            json=payload,
        )
        response.raise_for_status()
        return response.json()


def extract_response_text(response: dict) -> str:
    """Extract text content from Grok API response."""
    # The response structure may vary, handle common patterns
    if "output" in response:
        output = response["output"]
        if isinstance(output, list):
            # Combine all text outputs
            texts = []
            for item in output:
                if isinstance(item, dict):
                    # Check for message type with content
                    if item.get("type") == "message" and item.get("role") == "assistant":
                        content = item.get("content", [])
                        if isinstance(content, list):
                            for c in content:
                                if isinstance(c, dict) and c.get("type") == "output_text":
                                    texts.append(c.get("text", ""))
                    # Check for direct content field
                    elif "content" in item:
                        content = item["content"]
                        if isinstance(content, list):
                            for c in content:
                                if isinstance(c, dict):
                                    if c.get("type") == "output_text":
                                        texts.append(c.get("text", ""))
                                    elif c.get("type") == "text":
                                        texts.append(c.get("text", ""))
                        elif isinstance(content, str):
                            texts.append(content)
                    # Check for direct text field
                    elif "text" in item:
                        texts.append(item["text"])
            return "\n".join(texts) if texts else json.dumps(response, indent=2)
        elif isinstance(output, str):
            return output

    # Fallback: return full response as JSON
    return json.dumps(response, indent=2)


def extract_cost_footer(response: dict) -> str:
    """
    Build an optional footer line surfacing service_tier and cost from a Grok
    response's usage object. Returns "" if the response has no usage/cost info.

    1 USD = 10,000,000,000 (1e10) cost_in_usd_ticks, per xAI's cost-tracking docs.
    """
    usage = response.get("usage")
    if not isinstance(usage, dict):
        return ""

    parts = []
    service_tier = response.get("service_tier")
    if service_tier:
        parts.append(f"tier: {service_tier}")

    cost_ticks = usage.get("cost_in_usd_ticks")
    if isinstance(cost_ticks, (int, float)):
        cost_usd = cost_ticks / 1e10
        parts.append(f"cost: ${cost_usd:.6f}")

    if not parts:
        return ""

    return "\n\n---\n_" + " | ".join(parts) + "_"


# =============================================================================
# xAI Docs MCP Proxy
# =============================================================================

async def _call_docs_mcp(tool_name: str, arguments: dict) -> str:
    """Proxy a JSON-RPC tools/call to the xAI Docs MCP server (public, no auth)."""
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": arguments,
        },
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(
            XAI_DOCS_MCP_URL,
            json=payload,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
            },
            timeout=30.0,
        )
        response.raise_for_status()
        data = response.json()
    result = data.get("result", {})
    content = result.get("content", [])
    if content and isinstance(content, list):
        return content[0].get("text", str(result))
    return str(result)


# =============================================================================
# Tool Definitions
# =============================================================================

@server.list_tools()
async def list_tools() -> list[Tool]:
    """List all available Grok MCP tools."""
    return [
        Tool(
            name="grok-chat",
            description=(
                "Send a chat message to xAI's Grok model and get a response. "
                "Supports various Grok models including grok-4.20-0309-reasoning, grok-4, grok-4-1-fast, etc. "
                "Can include a custom system prompt for persona or instruction customization."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": "The user message to send to Grok",
                    },
                    "model": {
                        "type": "string",
                        "description": f"Grok model to use. Available: {', '.join(AVAILABLE_MODELS)}",
                        "default": DEFAULT_MODEL,
                        "enum": AVAILABLE_MODELS,
                    },
                    "system_prompt": {
                        "type": "string",
                        "description": (
                            "Optional system prompt to set context/persona. "
                            "Example: 'You are a helpful coding assistant.'"
                        ),
                    },
                    "conversation_history": {
                        "type": "array",
                        "description": (
                            "Optional conversation history as array of message objects. "
                            "Each object should have 'role' (user/assistant) and 'content' fields."
                        ),
                        "items": {
                            "type": "object",
                            "properties": {
                                "role": {
                                    "type": "string",
                                    "enum": ["user", "assistant"],
                                },
                                "content": {
                                    "type": "string",
                                },
                            },
                            "required": ["role", "content"],
                        },
                    },
                    "service_tier": {
                        "type": "string",
                        "description": (
                            "Optional priority processing tier. 'priority' applies a 2x "
                            "price premium to all token types for faster processing; "
                            "billing only applies if the response confirms priority was "
                            "actually used. Omit for standard 'default' tier."
                        ),
                        "enum": ["default", "priority"],
                    },
                },
                "required": ["message"],
            },
        ),
        Tool(
            name="grok-web-search",
            description=(
                "Search the web using Grok's web search capability. "
                "Returns AI-synthesized results from web sources. "
                "Supports domain filtering and image understanding."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query to execute",
                    },
                    "model": {
                        "type": "string",
                        "description": f"Grok model to use. Available: {', '.join(AVAILABLE_MODELS)}",
                        "default": DEFAULT_MODEL,
                        "enum": AVAILABLE_MODELS,
                    },
                    "allowed_domains": {
                        "type": "array",
                        "description": (
                            "Optional list of domains to restrict search to. "
                            "Example: ['wikipedia.org', 'github.com']"
                        ),
                        "items": {"type": "string"},
                    },
                    "excluded_domains": {
                        "type": "array",
                        "description": (
                            "Optional list of domains to exclude from search. "
                            "Example: ['pinterest.com', 'facebook.com']"
                        ),
                        "items": {"type": "string"},
                    },
                    "enable_image_understanding": {
                        "type": "boolean",
                        "description": "Enable understanding and analysis of images in search results",
                        "default": False,
                    },
                    "system_prompt": {
                        "type": "string",
                        "description": "Optional system prompt to customize response format or focus",
                    },
                    "service_tier": {
                        "type": "string",
                        "description": (
                            "Optional priority processing tier. 'priority' applies a 2x "
                            "price premium to all token types for faster processing; "
                            "billing only applies if the response confirms priority was "
                            "actually used. Omit for standard 'default' tier."
                        ),
                        "enum": ["default", "priority"],
                    },
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="grok-x-search",
            description=(
                "Search X (Twitter) posts using Grok's X search capability. "
                "Returns AI-synthesized results from X/Twitter. "
                "Supports filtering by handles, date range, and media understanding."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query for X/Twitter posts",
                    },
                    "model": {
                        "type": "string",
                        "description": f"Grok model to use. Available: {', '.join(AVAILABLE_MODELS)}",
                        "default": DEFAULT_MODEL,
                        "enum": AVAILABLE_MODELS,
                    },
                    "allowed_x_handles": {
                        "type": "array",
                        "description": (
                            "Optional list of X handles to restrict search to (without @). "
                            "Example: ['elonmusk', 'xai']"
                        ),
                        "items": {"type": "string"},
                    },
                    "excluded_x_handles": {
                        "type": "array",
                        "description": (
                            "Optional list of X handles to exclude from search (without @). "
                            "Example: ['spam_account', 'bot_account']"
                        ),
                        "items": {"type": "string"},
                    },
                    "from_date": {
                        "type": "string",
                        "description": (
                            "Start date for search range in ISO format (YYYY-MM-DD). "
                            "Example: '2024-01-01'"
                        ),
                    },
                    "to_date": {
                        "type": "string",
                        "description": (
                            "End date for search range in ISO format (YYYY-MM-DD). "
                            "Example: '2024-12-31'"
                        ),
                    },
                    "enable_image_understanding": {
                        "type": "boolean",
                        "description": "Enable understanding and analysis of images in posts",
                        "default": False,
                    },
                    "enable_video_understanding": {
                        "type": "boolean",
                        "description": "Enable understanding and analysis of videos in posts",
                        "default": False,
                    },
                    "system_prompt": {
                        "type": "string",
                        "description": "Optional system prompt to customize response format or focus",
                    },
                    "service_tier": {
                        "type": "string",
                        "description": (
                            "Optional priority processing tier. 'priority' applies a 2x "
                            "price premium to all token types for faster processing; "
                            "billing only applies if the response confirms priority was "
                            "actually used. Omit for standard 'default' tier."
                        ),
                        "enum": ["default", "priority"],
                    },
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="grok-models",
            description="List all available Grok models with their capabilities.",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        # Session Management Tools
        Tool(
            name="grok-session-create",
            description=(
                "Create a new conversation session with persistent history. "
                "Sessions allow you to maintain context across multiple interactions."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Optional human-readable name for the session",
                    },
                    "metadata": {
                        "type": "object",
                        "description": "Optional metadata to attach to the session",
                    },
                },
            },
        ),
        Tool(
            name="grok-session-list",
            description="List all active conversation sessions.",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        Tool(
            name="grok-session-get",
            description="Get detailed information about a specific session including conversation history.",
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "The session ID to retrieve",
                    },
                    "include_history": {
                        "type": "boolean",
                        "description": "Include full conversation history",
                        "default": True,
                    },
                },
                "required": ["session_id"],
            },
        ),
        Tool(
            name="grok-session-delete",
            description="Delete a conversation session and its history.",
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "The session ID to delete",
                    },
                },
                "required": ["session_id"],
            },
        ),
        Tool(
            name="grok-session-chat",
            description=(
                "Send a message within a session context. "
                "The session's conversation history is automatically included."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "The session ID to chat in",
                    },
                    "message": {
                        "type": "string",
                        "description": "The message to send",
                    },
                    "model": {
                        "type": "string",
                        "description": f"Grok model to use. Available: {', '.join(AVAILABLE_MODELS)}",
                        "default": DEFAULT_MODEL,
                        "enum": AVAILABLE_MODELS,
                    },
                    "system_prompt": {
                        "type": "string",
                        "description": "Optional system prompt to set context/persona",
                    },
                },
                "required": ["session_id", "message"],
            },
        ),
        # Tool Chaining Tools
        Tool(
            name="grok-chain-search-summarize",
            description=(
                "Chain operation: Search (web or X) and then summarize the results. "
                "Useful for quick research with condensed insights."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query",
                    },
                    "search_type": {
                        "type": "string",
                        "description": "Type of search to perform",
                        "enum": ["web", "x"],
                        "default": "web",
                    },
                    "model": {
                        "type": "string",
                        "description": f"Grok model to use. Available: {', '.join(AVAILABLE_MODELS)}",
                        "default": DEFAULT_MODEL,
                        "enum": AVAILABLE_MODELS,
                    },
                    "summary_instructions": {
                        "type": "string",
                        "description": "How to summarize the results",
                        "default": "Summarize the key findings in 3-5 bullet points",
                    },
                    "session_id": {
                        "type": "string",
                        "description": "Optional session ID to save chain execution to",
                    },
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="grok-chain-research",
            description=(
                "Chain operation: Multi-source research combining web + X search, "
                "then synthesize findings into a comprehensive report."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "description": "The research topic",
                    },
                    "model": {
                        "type": "string",
                        "description": f"Grok model to use. Available: {', '.join(AVAILABLE_MODELS)}",
                        "default": DEFAULT_MODEL,
                        "enum": AVAILABLE_MODELS,
                    },
                    "session_id": {
                        "type": "string",
                        "description": "Optional session ID to save chain execution to",
                    },
                },
                "required": ["topic"],
            },
        ),
        Tool(
            name="grok-chain-debug",
            description=(
                "Chain operation: Debug workflow that searches X for similar issues, "
                "then generates a fix based on findings. Great for troubleshooting errors."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "error_message": {
                        "type": "string",
                        "description": "The error message to debug",
                    },
                    "tech_stack": {
                        "type": "string",
                        "description": "Optional technology context (e.g., 'Python Flask', 'React')",
                    },
                    "model": {
                        "type": "string",
                        "description": f"Grok model to use. Available: {', '.join(AVAILABLE_MODELS)}",
                        "default": "grok-4",
                        "enum": AVAILABLE_MODELS,
                    },
                    "session_id": {
                        "type": "string",
                        "description": "Optional session ID to save chain execution to",
                    },
                },
                "required": ["error_message"],
            },
        ),
        # Image & Video Generation Tools
        Tool(
            name="grok-image-generate",
            description=(
                "Generate images from text prompts using xAI's Grok image models. "
                "Supports multiple aspect ratios, batch generation (up to 10 images), "
                "and returns either temporary URLs or base64-encoded image data. "
                "Available models: grok-imagine-image ($0.02/img), "
                "grok-imagine-image-quality ($0.05/img), grok-2-image-1212 ($0.07/img)."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "Text description of the image to generate",
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
                        "description": "Description of the desired changes",
                    },
                    "image_url": {
                        "type": "string",
                        "description": (
                            "Source image to edit. Accepts: "
                            "1) A public URL, or "
                            "2) A base64 data URI (e.g., 'data:image/jpeg;base64,...')"
                        ),
                    },
                    "model": {
                        "type": "string",
                        "description": "Image model to use for editing",
                        "default": "grok-imagine-image",
                        "enum": ["grok-imagine-image"],
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
                    "model": {
                        "type": "string",
                        "description": (
                            f"Video model to use. Available: {', '.join(VIDEO_MODELS)}. "
                            f"'{VIDEO_1080P_MODEL}' is required for 1080p resolution."
                        ),
                        "default": DEFAULT_VIDEO_MODEL,
                        "enum": VIDEO_MODELS,
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
                        "description": (
                            "Video resolution. Higher resolution costs more and takes longer. "
                            f"'1080p' is only supported on model='{VIDEO_1080P_MODEL}' "
                            "with image-to-video generation (image_url set, no video_url)."
                        ),
                        "default": "480p",
                        "enum": VIDEO_RESOLUTIONS,
                    },
                },
                "required": ["prompt"],
            },
        ),
        # Text-to-Speech tool
        Tool(
            name="grok-tts",
            description=(
                "Convert text to speech using xAI's Grok TTS model. "
                f"Available voices: {', '.join(TTS_VOICES)}. "
                "Returns synthesized audio (MP3) plus optional word-level timestamps."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "Text to synthesize (max 15,000 characters). Supports speech tags like [pause] and <whisper>.",
                    },
                    "voice": {
                        "type": "string",
                        "description": "Voice to use for synthesis",
                        "default": DEFAULT_TTS_VOICE,
                        "enum": TTS_VOICES,
                    },
                    "language": {
                        "type": "string",
                        "description": "BCP-47 language code (e.g. 'en', 'zh') or 'auto' to detect from the text",
                        "default": "auto",
                    },
                    "speed": {
                        "type": "number",
                        "description": "Speech speed multiplier",
                        "default": 1.0,
                        "minimum": 0.7,
                        "maximum": 1.5,
                    },
                    "with_timestamps": {
                        "type": "boolean",
                        "description": "Include a word-level timestamp table in the tool's text output",
                        "default": False,
                    },
                },
                "required": ["text"],
            },
        ),
        # xAI Docs tools
        Tool(
            name="grok-docs-list",
            description=(
                "List all available xAI documentation pages. "
                "Returns page titles and slugs you can use with grok-docs-get."
            ),
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        Tool(
            name="grok-docs-search",
            description=(
                "Search the xAI documentation. Returns relevant pages matching the query. "
                "Use for finding API docs, model specs, pricing, and feature guides."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query string",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results to return",
                        "default": 5,
                    },
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="grok-docs-get",
            description=(
                "Retrieve the full content of an xAI documentation page by slug. "
                "Use grok-docs-list or grok-docs-search first to find the correct slug."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "slug": {
                        "type": "string",
                        "description": "Page slug identifier (e.g. 'quickstart', 'models', 'api-reference')",
                    },
                },
                "required": ["slug"],
            },
        ),
    ]


# =============================================================================
# Tool Implementations
# =============================================================================

def _check_rate_limit(key: str | None) -> CallToolResult | None:
    """Returns error result if rate limited, None if OK."""
    result = validate_key(key if key else None)
    if result["tier"] == "free" and not check_free_limit(key):
        return CallToolResult(
            content=[TextContent(type="text", text=(
                "xBridge free tier limit reached (50 calls/day). "
                "Upgrade to Pro at https://xbridgemcp.com"
            ))],
            isError=True,
        )
    return None

@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> CallToolResult:
    """Handle tool invocations."""
    try:
        if limit := _check_rate_limit(os.environ.get("XBRIDGE_KEY", "")):
            return limit

        # Original tools
        if name == "grok-chat":
            return await handle_grok_chat(arguments)
        elif name == "grok-web-search":
            return await handle_grok_web_search(arguments)
        elif name == "grok-x-search":
            return await handle_grok_x_search(arguments)
        elif name == "grok-models":
            return await handle_grok_models(arguments)
        # Session management tools
        elif name == "grok-session-create":
            return await handle_session_create(arguments)
        elif name == "grok-session-list":
            return await handle_session_list(arguments)
        elif name == "grok-session-get":
            return await handle_session_get(arguments)
        elif name == "grok-session-delete":
            return await handle_session_delete(arguments)
        elif name == "grok-session-chat":
            return await handle_session_chat(arguments)
        # Tool chaining tools
        elif name == "grok-chain-search-summarize":
            return await handle_chain_search_summarize(arguments)
        elif name == "grok-chain-research":
            return await handle_chain_research(arguments)
        elif name == "grok-chain-debug":
            return await handle_chain_debug(arguments)
        # Image & Video generation tools
        elif name == "grok-image-generate":
            return await handle_image_generate(arguments)
        elif name == "grok-image-edit":
            return await handle_image_edit(arguments)
        elif name == "grok-image-models":
            return await handle_image_models(arguments)
        elif name == "grok-video-generate":
            return await handle_video_generate(arguments)
        elif name == "grok-tts":
            return await handle_grok_tts(arguments)
        # xAI Docs tools
        elif name == "grok-docs-list":
            return await handle_docs_list(arguments)
        elif name == "grok-docs-search":
            return await handle_docs_search(arguments)
        elif name == "grok-docs-get":
            return await handle_docs_get(arguments)
        else:
            return CallToolResult(
                content=[TextContent(type="text", text=f"Unknown tool: {name}")],
                isError=True,
            )
    except Exception as e:
        return CallToolResult(
            content=[TextContent(type="text", text=f"Error: {str(e)}")],
            isError=True,
        )


async def handle_grok_chat(arguments: dict[str, Any]) -> CallToolResult:
    """Handle grok-chat tool invocation."""
    message = arguments.get("message")
    if not message:
        return CallToolResult(
            content=[TextContent(type="text", text="Error: 'message' is required")],
            isError=True,
        )

    model = arguments.get("model", DEFAULT_MODEL)
    system_prompt = arguments.get("system_prompt")
    conversation_history = arguments.get("conversation_history", [])
    service_tier = arguments.get("service_tier")

    # Build messages list
    messages = list(conversation_history)
    messages.append({"role": "user", "content": message})

    response = await make_grok_request(
        messages=messages,
        model=model,
        system_prompt=system_prompt,
        service_tier=service_tier,
    )

    result_text = extract_response_text(response) + extract_cost_footer(response)

    return CallToolResult(
        content=[TextContent(type="text", text=result_text)],
    )


async def handle_grok_web_search(arguments: dict[str, Any]) -> CallToolResult:
    """Handle grok-web-search tool invocation."""
    query = arguments.get("query")
    if not query:
        return CallToolResult(
            content=[TextContent(type="text", text="Error: 'query' is required")],
            isError=True,
        )

    model = arguments.get("model", DEFAULT_MODEL)
    system_prompt = arguments.get("system_prompt")
    service_tier = arguments.get("service_tier")

    # Build web search tool configuration
    web_search_tool: dict[str, Any] = {"type": "web_search"}

    # Add optional filters
    if arguments.get("allowed_domains"):
        web_search_tool["allowed_domains"] = arguments["allowed_domains"]
    if arguments.get("excluded_domains"):
        web_search_tool["excluded_domains"] = arguments["excluded_domains"]
    if arguments.get("enable_image_understanding"):
        web_search_tool["enable_image_understanding"] = True

    messages = [{"role": "user", "content": query}]

    response = await make_grok_request(
        messages=messages,
        model=model,
        tools=[web_search_tool],
        system_prompt=system_prompt,
        service_tier=service_tier,
    )

    result_text = extract_response_text(response) + extract_cost_footer(response)

    return CallToolResult(
        content=[TextContent(type="text", text=result_text)],
    )


async def handle_grok_x_search(arguments: dict[str, Any]) -> CallToolResult:
    """Handle grok-x-search tool invocation."""
    query = arguments.get("query")
    if not query:
        return CallToolResult(
            content=[TextContent(type="text", text="Error: 'query' is required")],
            isError=True,
        )

    model = arguments.get("model", DEFAULT_MODEL)
    system_prompt = arguments.get("system_prompt")
    service_tier = arguments.get("service_tier")

    # Build X search tool configuration
    x_search_tool: dict[str, Any] = {"type": "x_search"}

    # Add optional filters
    if arguments.get("allowed_x_handles"):
        x_search_tool["allowed_x_handles"] = arguments["allowed_x_handles"]
    if arguments.get("excluded_x_handles"):
        x_search_tool["excluded_x_handles"] = arguments["excluded_x_handles"]
    if arguments.get("from_date"):
        x_search_tool["from_date"] = arguments["from_date"]
    if arguments.get("to_date"):
        x_search_tool["to_date"] = arguments["to_date"]
    if arguments.get("enable_image_understanding"):
        x_search_tool["enable_image_understanding"] = True
    if arguments.get("enable_video_understanding"):
        x_search_tool["enable_video_understanding"] = True

    messages = [{"role": "user", "content": query}]

    response = await make_grok_request(
        messages=messages,
        model=model,
        tools=[x_search_tool],
        system_prompt=system_prompt,
        service_tier=service_tier,
    )

    result_text = extract_response_text(response) + extract_cost_footer(response)

    return CallToolResult(
        content=[TextContent(type="text", text=result_text)],
    )


async def handle_grok_models(arguments: dict[str, Any]) -> CallToolResult:
    """Handle grok-models tool invocation."""
    region_note = f"Region: {_XAI_REGION or 'global (auto-routed)'}"
    models_info = f"""# Available Grok Text Models
**Endpoint**: {_XAI_HOST} | **{region_note}**

## grok-4.20 Family (Latest)

### grok-4.20-0309-reasoning
- **Context**: 1M tokens | **Input**: Text + Image
- **Capabilities**: Reasoning, Function Calling, Structured Output
- **Pricing**: $1.25/$2.50 per 1M tokens (in/out)

### grok-4.20-0309-non-reasoning
- **Context**: 1M tokens | **Input**: Text + Image
- **Capabilities**: Function Calling, Structured Output
- **Pricing**: $1.25/$2.50 per 1M tokens (in/out)

### grok-4.20-multi-agent-0309
- **Context**: 1M tokens | **Input**: Text + Image
- **Capabilities**: Reasoning, Function Calling, Structured Output, Multi-Agent
- **Pricing**: $1.25/$2.50 per 1M tokens (in/out)
- **Best For**: Agentic workflows, orchestration, multi-step tasks

## Flagship Models

### grok-4.3
- **Context**: 1M tokens | **Input**: Text + Image
- **Capabilities**: Reasoning, Function Calling, Structured Output
- **Pricing**: $1.25/$2.50 per 1M tokens (in/out)
- **Best For**: General chat, coding, reasoning — recommended default

### grok-build-0.1
- **Context**: 256K tokens
- **Capabilities**: Coding-focused (replaces retired `grok-code-fast-1`)
- **Pricing**: $1.00/$2.00 per 1M tokens (in/out)
- **Best For**: Code generation, refactoring, coding agents

## Legacy Models (retirement status vs xAI's May-15-2026 model sunset unconfirmed)

These slugs are kept for backward compatibility. xAI's current pricing/models docs no
longer list them — they may be redirected to `grok-4.3` billing, retired outright, or
still resolving as-is. Verify liveness with a live probe before relying on them.

### grok-4
- **Context**: 256K tokens | **Input**: Text + Image
- **Capabilities**: Reasoning, Function Calling, Structured Output
- **Pricing**: last known $3.00/$15.00 per 1M tokens (in/out) — unconfirmed current

### grok-4-1-fast
- **Context**: 2M tokens | **Input**: Text + Image
- **Capabilities**: Function Calling, Structured Output
- **Pricing**: last known $0.20/$0.50 per 1M tokens (in/out) — unconfirmed current | **Speed**: Fast

### grok-3-fast / grok-3-mini
- **Context**: 131K tokens | **Pricing**: last known $0.30/$0.50 — unconfirmed current | Reasoning capable

### grok-2 / grok-2-latest
- **Context**: 32K tokens | **Pricing**: last known $2.00/$10.00 — unconfirmed current

### grok-2-vision-1212
- **Context**: 32K tokens | **Input**: Text + Image | **Pricing**: last known $2.00/$10.00 — unconfirmed current

## Tool Capabilities

All models support web search and X search via the Responses API.
For image/video models, use `grok-image-models` tool.
"""

    return CallToolResult(
        content=[TextContent(type="text", text=models_info)],
    )


# =============================================================================
# Session Management Tool Handlers
# =============================================================================

async def handle_session_create(arguments: dict[str, Any]) -> CallToolResult:
    """Handle grok-session-create tool invocation."""
    session_manager = get_session_manager()

    name = arguments.get("name")
    metadata = arguments.get("metadata")

    session_id = session_manager.create_session(name=name, metadata=metadata)

    result = f"""# Session Created

**Session ID:** `{session_id}`
**Name:** {name or f"Session {session_id[:8]}"}
**Created:** {session_manager.get_session(session_id)['created_at']}

Use this session ID with `grok-session-chat` to maintain conversation context.
"""

    return CallToolResult(
        content=[TextContent(type="text", text=result)],
    )


async def handle_session_list(arguments: dict[str, Any]) -> CallToolResult:
    """Handle grok-session-list tool invocation."""
    session_manager = get_session_manager()
    sessions = session_manager.list_sessions()

    if not sessions:
        result = "No active sessions found. Create one with `grok-session-create`."
    else:
        result = "# Active Sessions\n\n"
        for session in sessions:
            result += f"""## {session['name']}
- **ID:** `{session['session_id']}`
- **Created:** {session['created_at']}
- **Updated:** {session['updated_at']}
- **Messages:** {session['message_count']}

"""

    return CallToolResult(
        content=[TextContent(type="text", text=result)],
    )


async def handle_session_get(arguments: dict[str, Any]) -> CallToolResult:
    """Handle grok-session-get tool invocation."""
    session_id = arguments.get("session_id")
    include_history = arguments.get("include_history", True)

    session_manager = get_session_manager()
    session = session_manager.get_session(session_id)

    if not session:
        return CallToolResult(
            content=[TextContent(type="text", text=f"Session {session_id} not found")],
            isError=True,
        )

    result = f"""# Session: {session['name']}

**ID:** `{session['session_id']}`
**Created:** {session['created_at']}
**Updated:** {session['updated_at']}
**Messages:** {len(session['conversation_history'])}
"""

    if include_history and session['conversation_history']:
        result += "\n## Conversation History\n\n"
        for msg in session['conversation_history']:
            role = msg['role'].upper()
            result += f"**{role}:** {msg['content'][:200]}{'...' if len(msg['content']) > 200 else ''}\n\n"

    return CallToolResult(
        content=[TextContent(type="text", text=result)],
    )


async def handle_session_delete(arguments: dict[str, Any]) -> CallToolResult:
    """Handle grok-session-delete tool invocation."""
    session_id = arguments.get("session_id")

    session_manager = get_session_manager()
    session_manager.delete_session(session_id)

    return CallToolResult(
        content=[TextContent(type="text", text=f"Session {session_id} deleted successfully")],
    )


async def handle_session_chat(arguments: dict[str, Any]) -> CallToolResult:
    """Handle grok-session-chat tool invocation."""
    session_id = arguments.get("session_id")
    message = arguments.get("message")
    model = arguments.get("model", DEFAULT_MODEL)
    system_prompt = arguments.get("system_prompt")

    if not message:
        return CallToolResult(
            content=[TextContent(type="text", text="Error: 'message' is required")],
            isError=True,
        )

    session_manager = get_session_manager()
    session = session_manager.get_session(session_id)

    if not session:
        return CallToolResult(
            content=[TextContent(type="text", text=f"Session {session_id} not found")],
            isError=True,
        )

    # Get conversation history
    history = session_manager.get_conversation_history(session_id, format_for_api=True)

    # Add new user message
    messages = list(history)
    messages.append({"role": "user", "content": message})

    # Make Grok request
    response = await make_grok_request(
        messages=messages,
        model=model,
        system_prompt=system_prompt,
    )

    result_text = extract_response_text(response)

    # Save to session history
    session_manager.add_message(session_id, "user", message, {"model": model})
    session_manager.add_message(session_id, "assistant", result_text, {"model": model})

    return CallToolResult(
        content=[TextContent(type="text", text=result_text)],
    )


# =============================================================================
# Tool Chaining Handlers
# =============================================================================

async def handle_chain_search_summarize(arguments: dict[str, Any]) -> CallToolResult:
    """Handle grok-chain-search-summarize tool invocation."""
    query = arguments.get("query")
    search_type = arguments.get("search_type", "web")
    model = arguments.get("model", DEFAULT_MODEL)
    summary_instructions = arguments.get("summary_instructions", "Summarize the key findings in 3-5 bullet points")
    session_id = arguments.get("session_id")

    # Select search tool
    if search_type == "web":
        search_func = lambda **kwargs: handle_grok_web_search(kwargs)
    else:
        search_func = lambda **kwargs: handle_grok_x_search(kwargs)

    chat_func = lambda **kwargs: handle_grok_chat(kwargs)

    # Build and execute chain
    chain = ChainBuilder.search_and_summarize(
        search_tool=search_func,
        chat_tool=chat_func,
        search_query=query,
        search_type=search_type,
        model=model,
        summary_instructions=summary_instructions,
    )

    # Execute chain
    chain_result = await execute_chain_with_extraction(chain)

    # Save to session if provided
    if session_id:
        session_manager = get_session_manager()
        for i, step_result in enumerate(chain_result["step_results"]):
            session_manager.add_tool_chain_step(
                session_id,
                step_name=f"chain_step_{i}",
                tool_name=step_result.get("step_name", "unknown"),
                arguments=arguments,
                result=step_result,
            )

    # Format result
    result_text = f"""# Search & Summarize Chain

**Query:** {query}
**Search Type:** {search_type}
**Status:** {'✓ Success' if chain_result['success'] else '✗ Failed'}

## Results

{chain_result.get('final_result_text', 'No result')}
"""

    return CallToolResult(
        content=[TextContent(type="text", text=result_text)],
    )


async def handle_chain_research(arguments: dict[str, Any]) -> CallToolResult:
    """Handle grok-chain-research tool invocation."""
    topic = arguments.get("topic")
    model = arguments.get("model", DEFAULT_MODEL)
    session_id = arguments.get("session_id")

    web_search_func = lambda **kwargs: handle_grok_web_search(kwargs)
    x_search_func = lambda **kwargs: handle_grok_x_search(kwargs)
    chat_func = lambda **kwargs: handle_grok_chat(kwargs)

    # Build and execute chain
    chain = ChainBuilder.multi_source_research(
        web_search_tool=web_search_func,
        x_search_tool=x_search_func,
        chat_tool=chat_func,
        topic=topic,
        model=model,
    )

    chain_result = await execute_chain_with_extraction(chain)

    # Save to session if provided
    if session_id:
        session_manager = get_session_manager()
        for i, step_result in enumerate(chain_result["step_results"]):
            session_manager.add_tool_chain_step(
                session_id,
                step_name=f"research_step_{i}",
                tool_name=step_result.get("step_name", "unknown"),
                arguments=arguments,
                result=step_result,
            )

    result_text = f"""# Multi-Source Research Chain

**Topic:** {topic}
**Status:** {'✓ Success' if chain_result['success'] else '✗ Failed'}

## Research Report

{chain_result.get('final_result_text', 'No result')}
"""

    return CallToolResult(
        content=[TextContent(type="text", text=result_text)],
    )


async def handle_chain_debug(arguments: dict[str, Any]) -> CallToolResult:
    """Handle grok-chain-debug tool invocation."""
    error_message = arguments.get("error_message")
    tech_stack = arguments.get("tech_stack")
    model = arguments.get("model", "grok-4")
    session_id = arguments.get("session_id")

    x_search_func = lambda **kwargs: handle_grok_x_search(kwargs)
    chat_func = lambda **kwargs: handle_grok_chat(kwargs)

    # Build and execute chain
    chain = ChainBuilder.debug_workflow(
        x_search_tool=x_search_func,
        chat_tool=chat_func,
        error_message=error_message,
        tech_stack=tech_stack,
        model=model,
    )

    chain_result = await execute_chain_with_extraction(chain)

    # Save to session if provided
    if session_id:
        session_manager = get_session_manager()
        for i, step_result in enumerate(chain_result["step_results"]):
            session_manager.add_tool_chain_step(
                session_id,
                step_name=f"debug_step_{i}",
                tool_name=step_result.get("step_name", "unknown"),
                arguments=arguments,
                result=step_result,
            )

    result_text = f"""# Debug Workflow Chain

**Error:** {error_message}
**Tech Stack:** {tech_stack or 'Not specified'}
**Status:** {'✓ Success' if chain_result['success'] else '✗ Failed'}

## Debug Analysis & Fix

{chain_result.get('final_result_text', 'No result')}
"""

    return CallToolResult(
        content=[TextContent(type="text", text=result_text)],
    )


# =============================================================================
# Image & Video Generation Handlers
# =============================================================================

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

        # API returns "b64_json" field; SDK docs call it "image" — handle both
        b64_data = img_data.get("b64_json") or img_data.get("image")
        if response_format == "b64_json" and b64_data:
            content.append(ImageContent(
                type="image",
                data=b64_data,
                mimeType="image/jpeg",
            ))
            content.append(TextContent(
                type="text",
                text=f"*{label} (base64 embedded)*\n"
            ))
        elif "url" in img_data:
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
            content.append(TextContent(
                type="text",
                text=f"\n**{label}**: {json.dumps(img_data, indent=2)}\n"
            ))

    return CallToolResult(content=content)


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

### grok-imagine-image-quality
- **Type**: Image generation + editing (higher fidelity)
- **Input**: Text prompt, optional source image (for edits)
- **Price**: $0.05 per image
- **Rate Limit**: 300 requests/minute
- **Features**: Same as grok-imagine-image, higher-quality output; replaces retired grok-imagine-image-pro
- **Best For**: Final/polished output where quality matters more than cost

### grok-2-image-1212
- **Type**: Legacy text-to-image
- **Input**: Text prompt only
- **Price**: $0.07 per image (last known -- no current doc presence, unconfirmed)
- **Rate Limit**: 300 requests/minute
- **Features**: Text-to-image generation only (no editing support)
- **Best For**: Backward compatibility, specific style preferences

## Video Generation Models

### grok-imagine-video
- **Type**: Video generation (async)
- **Input**: Text prompt, optional source image/video
- **Price**: $0.05/sec (480p) | $0.07/sec (720p)
- **Rate Limit**: 60 requests/minute
- **Features**: Text-to-video, image-to-video, video editing
- **Duration**: 1-15 seconds (generation), max 8.7s input (editing)
- **Resolutions**: 480p ($0.05/sec) | 720p ($0.07/sec) -- 1080p not supported on this model
- **Aspect Ratios**: 1:1, 16:9, 9:16, 4:3, 3:4, 3:2, 2:3
- **Best For**: Short video clips, animations, product demos

### grok-imagine-video-1.5
- **Type**: Video generation (async), higher tier
- **Input**: Text prompt, optional source image/video
- **Price**: $0.080/sec
- **Rate Limit**: 60 requests/minute
- **Features**: Text-to-video, image-to-video, video editing
- **Duration**: 1-15 seconds (generation), max 8.7s input (editing)
- **Resolutions**: 480p, 720p, and **1080p** -- 1080p only for image-to-video generation
- **Aspect Ratios**: 1:1, 16:9, 9:16, 4:3, 3:4, 3:2, 2:3
- **Best For**: Highest-resolution output, image-to-video at 1080p

## Output Formats

- **url**: Returns temporary download URL (expires quickly -- download immediately)
- **b64_json**: Returns base64-encoded JPEG data (embedded in response, no expiry)
"""

    return CallToolResult(
        content=[TextContent(type="text", text=models_info)],
    )


async def handle_video_generate(arguments: dict[str, Any]) -> CallToolResult:
    """Handle grok-video-generate tool invocation."""
    prompt = arguments.get("prompt")
    if not prompt:
        return CallToolResult(
            content=[TextContent(type="text", text="Error: 'prompt' is required")],
            isError=True,
        )

    model = arguments.get("model", DEFAULT_VIDEO_MODEL)
    image_url = arguments.get("image_url")
    video_url = arguments.get("video_url")
    duration = arguments.get("duration", 5)
    aspect_ratio = arguments.get("aspect_ratio", "16:9")
    resolution = arguments.get("resolution", "480p")

    if video_url:
        gen_type = "video editing"
    elif image_url:
        gen_type = "image-to-video"
    else:
        gen_type = "text-to-video"

    if resolution == "1080p" and (model != VIDEO_1080P_MODEL or gen_type != "image-to-video"):
        return CallToolResult(
            content=[TextContent(
                type="text",
                text=(
                    "Error: '1080p' resolution is only supported on "
                    f"'{VIDEO_1080P_MODEL}' for image-to-video generation "
                    f"(got model='{model}', mode='{gen_type}')."
                ),
            )],
            isError=True,
        )

    try:
        response = await make_video_request(
            prompt=prompt,
            model=model,
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
"""

    return CallToolResult(
        content=[TextContent(type="text", text=result_text)],
    )


async def handle_grok_tts(arguments: dict[str, Any]) -> CallToolResult:
    """Handle grok-tts tool invocation."""
    text = arguments.get("text")
    if not text:
        return CallToolResult(
            content=[TextContent(type="text", text="Error: 'text' is required")],
            isError=True,
        )

    voice = arguments.get("voice", DEFAULT_TTS_VOICE)
    language = arguments.get("language", "auto")
    speed = arguments.get("speed", 1.0)
    with_timestamps = arguments.get("with_timestamps", False)

    response = await make_tts_request(
        text=text,
        voice_id=voice,
        language=language,
        speed=speed,
    )

    audio_b64 = response.get("audio", "")
    content_type = response.get("content_type", "audio/mpeg")
    duration = response.get("duration", "unknown")

    content: list[Any] = [
        TextContent(
            type="text",
            text=f"**Speech synthesized** | Voice: `{voice}` | Duration: {duration}s\n",
        ),
    ]

    if audio_b64:
        content.append(AudioContent(type="audio", data=audio_b64, mimeType=content_type))

    if with_timestamps:
        timestamps = response.get("audio_timestamps", {})
        chars = timestamps.get("graph_chars", [])
        times = timestamps.get("graph_times", [])
        if chars and times:
            rows = "\n".join(
                f"| `{ch}` | {t[0]:.2f}s | {t[1]:.2f}s |"
                for ch, t in zip(chars, times)
            )
            content.append(TextContent(
                type="text",
                text=f"\n| Char | Start | End |\n|---|---|---|\n{rows}\n",
            ))

    return CallToolResult(content=content)


# =============================================================================
# xAI Docs Tool Handlers
# =============================================================================

async def handle_docs_list(arguments: dict[str, Any]) -> CallToolResult:
    """Handle grok-docs-list tool invocation."""
    try:
        text = await _call_docs_mcp("list_doc_pages", {})
        return CallToolResult(content=[TextContent(type="text", text=text)])
    except httpx.HTTPStatusError as e:
        return CallToolResult(
            content=[TextContent(type="text", text=f"Docs API error: {e.response.status_code}")],
            isError=True,
        )
    except Exception as e:
        return CallToolResult(
            content=[TextContent(type="text", text=f"Error fetching docs list: {str(e)}")],
            isError=True,
        )


async def handle_docs_get(arguments: dict[str, Any]) -> CallToolResult:
    """Handle grok-docs-get tool invocation."""
    slug = arguments.get("slug")
    if not slug:
        return CallToolResult(
            content=[TextContent(type="text", text="Error: 'slug' is required")],
            isError=True,
        )
    try:
        text = await _call_docs_mcp("get_doc_page", {"slug": slug})
        return CallToolResult(content=[TextContent(type="text", text=text)])
    except httpx.HTTPStatusError as e:
        return CallToolResult(
            content=[TextContent(type="text", text=f"Docs API error: {e.response.status_code}")],
            isError=True,
        )
    except Exception as e:
        return CallToolResult(
            content=[TextContent(type="text", text=f"Error fetching doc page: {str(e)}")],
            isError=True,
        )


async def handle_docs_search(arguments: dict[str, Any]) -> CallToolResult:
    """Handle grok-docs-search tool invocation."""
    query = arguments.get("query")
    if not query:
        return CallToolResult(
            content=[TextContent(type="text", text="Error: 'query' is required")],
            isError=True,
        )
    limit = arguments.get("limit", 5)
    try:
        text = await _call_docs_mcp("search_docs", {"query": query, "limit": limit})
        return CallToolResult(content=[TextContent(type="text", text=text)])
    except httpx.HTTPStatusError as e:
        return CallToolResult(
            content=[TextContent(type="text", text=f"Docs API error: {e.response.status_code}")],
            isError=True,
        )
    except Exception as e:
        return CallToolResult(
            content=[TextContent(type="text", text=f"Error searching docs: {str(e)}")],
            isError=True,
        )


async def execute_chain_with_extraction(chain) -> dict:
    """Execute a chain and extract text from CallToolResult objects."""
    result = await chain.execute()

    # Extract text from final result if it's a CallToolResult
    if result.get("final_result"):
        final_result = result["final_result"]
        if isinstance(final_result, CallToolResult):
            # Extract text content
            text_parts = []
            for content in final_result.content:
                if hasattr(content, 'text'):
                    text_parts.append(content.text)
            result["final_result_text"] = "\n".join(text_parts)
        else:
            result["final_result_text"] = str(final_result)

    # Also extract text from step results
    for step_result in result.get("step_results", []):
        if "result" in step_result:
            step_res = step_result["result"]
            if isinstance(step_res, CallToolResult):
                text_parts = []
                for content in step_res.content:
                    if hasattr(content, 'text'):
                        text_parts.append(content.text)
                step_result["result_text"] = "\n".join(text_parts)

    return result


# =============================================================================
# Main Entry Point
# =============================================================================

async def main():
    """Run the xBridge MCP server with optional license key validation."""
    xbridge_key = os.environ.get("XBRIDGE_KEY", "")
    result = validate_key(xbridge_key if xbridge_key else None)

    if not result["valid"]:
        print(f"[xbridge] WARNING: Invalid license key — {result.get('reason')}. Free tier active.",
              file=sys.stderr)
    elif result["tier"] == "free":
        print("[xbridge] Free tier active (50 calls/day, no key)", file=sys.stderr)
    else:
        print(f"[xbridge] {result['tier'].upper()} tier active — unlimited calls", file=sys.stderr)

    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


def run():
    """Sync entry point for console_scripts / CLI."""
    asyncio.run(main())


if __name__ == "__main__":
    run()
