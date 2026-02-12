#!/usr/bin/env python3
"""
Grok MCP Server - xAI Grok API Integration

Provides MCP tools for interacting with xAI's Grok API including:
- Chat completions with various Grok models
- Web search with domain filtering
- X (Twitter) search with handle and date filtering
- Session management for persistent conversation history
- Tool chaining for multi-step workflows (search → summarize, research, debug)
"""

import os
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
    CallToolResult,
)

# Import session management and tool chaining
from .session_manager import get_session_manager
from .tool_chains import ChainBuilder

# Constants
XAI_API_BASE = "https://api.x.ai/v1/responses"
DEFAULT_MODEL = "grok-4-1-fast"
AVAILABLE_MODELS = [
    "grok-4",
    "grok-4-1-fast",
    "grok-4-1-fast-reasoning",
    "grok-4-1-fast-non-reasoning",
    "grok-4-0709",
    "grok-code-fast-1",
    "grok-3",
    "grok-3-fast",
    "grok-3-mini",
    "grok-2",
    "grok-2-latest",
    "grok-2-vision-1212",
]

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

# Initialize MCP Server
server = Server("grok-mcp-server")


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
) -> dict:
    """
    Make a request to the xAI Grok API.

    Args:
        messages: List of message objects with role and content
        model: Grok model to use
        tools: Optional list of tool configurations
        system_prompt: Optional system prompt to prepend

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

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }

    async with httpx.AsyncClient(timeout=300.0) as client:
        response = await client.post(
            XAI_API_BASE,
            headers=headers,
            json=payload,
        )
        response.raise_for_status()
        return response.json()


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

            if status == "done":
                return poll_data
            elif status == "expired":
                raise RuntimeError(
                    f"Video generation expired for request {request_id}. "
                    "The request took too long on the server side."
                )

        raise TimeoutError(
            f"Video generation timed out after {VIDEO_POLL_TIMEOUT}s "
            f"for request {request_id}."
        )


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
                "Supports various Grok models including grok-4, grok-4-1-fast, etc. "
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
                "Available models: grok-imagine-image ($0.02/img), grok-imagine-image-pro ($0.07/img)."
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
    ]


# =============================================================================
# Tool Implementations
# =============================================================================

@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> CallToolResult:
    """Handle tool invocations."""
    try:
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

    # Build messages list
    messages = list(conversation_history)
    messages.append({"role": "user", "content": message})

    response = await make_grok_request(
        messages=messages,
        model=model,
        system_prompt=system_prompt,
    )

    result_text = extract_response_text(response)

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
    )

    result_text = extract_response_text(response)

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
    )

    result_text = extract_response_text(response)

    return CallToolResult(
        content=[TextContent(type="text", text=result_text)],
    )


async def handle_grok_models(arguments: dict[str, Any]) -> CallToolResult:
    """Handle grok-models tool invocation."""
    models_info = """# Available Grok Text Models

## Flagship Models

### grok-4
- **Context**: 256K tokens | **Input**: Text + Image
- **Capabilities**: Reasoning, Function Calling, Structured Output
- **Pricing**: $3.00/$15.00 per 1M tokens (in/out)

### grok-4-1-fast
- **Context**: 2M tokens | **Input**: Text + Image
- **Capabilities**: Function Calling, Structured Output
- **Pricing**: $0.20/$0.50 per 1M tokens (in/out) | **Speed**: Fast

### grok-4-1-fast-reasoning
- **Context**: 2M tokens | **Input**: Text + Image
- **Capabilities**: Reasoning, Function Calling, Structured Output
- **Pricing**: $0.20/$0.50 per 1M tokens (in/out)

### grok-4-0709
- **Context**: 256K tokens | **Input**: Text + Image
- **Capabilities**: Reasoning, Function Calling, Structured Output
- **Pricing**: $3.00/$15.00 per 1M tokens (in/out)

## Specialized Models

### grok-code-fast-1
- **Context**: 256K tokens | **Input**: Text only
- **Capabilities**: Reasoning, Function Calling, Structured Output
- **Pricing**: $0.20/$1.50 per 1M tokens (in/out)
- **Best For**: Code generation and analysis

## Previous Generation

### grok-3 / grok-3-fast
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

        if response_format == "b64_json" and "image" in img_data:
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
    """Run the Grok MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
