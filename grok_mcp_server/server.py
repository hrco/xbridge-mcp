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
    "grok-3",
    "grok-3-fast",
    "grok-2",
    "grok-2-latest",
]

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
    models_info = """# Available Grok Models

## Production Models

### grok-4
- **Description**: Latest flagship model with highest capability
- **Best for**: Complex reasoning, analysis, and creative tasks
- **Speed**: Standard

### grok-4-1-fast
- **Description**: Optimized version of grok-4 for faster responses
- **Best for**: Real-time applications, quick queries
- **Speed**: Fast

### grok-3
- **Description**: Previous generation flagship model
- **Best for**: General purpose tasks with proven reliability
- **Speed**: Standard

### grok-3-fast
- **Description**: Fast variant of grok-3
- **Best for**: Quick responses with good capability
- **Speed**: Fast

### grok-2
- **Description**: Stable, well-tested model
- **Best for**: Production workloads requiring consistency
- **Speed**: Standard

### grok-2-latest
- **Description**: Latest updates to grok-2 line
- **Best for**: Updated capabilities with grok-2 base
- **Speed**: Standard

## Tool Capabilities

All models support:
- **Web Search**: Search the internet with domain filtering
- **X Search**: Search X/Twitter with handle and date filtering
- **Image Understanding**: Analyze images in search results (when enabled)
- **Video Understanding**: Analyze videos in X posts (when enabled, X Search only)
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
