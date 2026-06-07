# Tools Reference

> All 19 MCP tools available through xBridge MCP. Each tool is callable from Claude Code once connected.

## Chat

### grok-chat

Send a message to Grok and get a response.

```
Parameters:
| Name | Type | Required | Description |
|------|------|----------|-------------|
| message | string | Yes | The message to send to Grok |
| model | string | No | Model to use (default: grok-4-1-fast) |
| system_prompt | string | No | Custom system prompt for persona |
| conversation_history | array | No | Prior messages for context |

Available models:
grok-4, grok-4-1-fast, grok-3, grok-3-fast, grok-3-mini, grok-2, grok-2-latest
```

Example: *"Ask Grok to explain async/await in Python"*

### grok-models

List all available Grok models.

```
Parameters: none
```

---

## Search

### grok-web-search

Search the live web via Grok.

```
Parameters:
| Name | Type | Required | Description |
|------|------|----------|-------------|
| query | string | Yes | Search query |
| model | string | No | Model to use |
```

Example: *"Search the web for latest MCP server projects"*

### grok-x-search

Search X/Twitter in real time.

```
Parameters:
| Name | Type | Required | Description |
|------|------|----------|-------------|
| query | string | Yes | X/Twitter search query |
| model | string | No | Model to use |
```

Example: *"Search X for what people are saying about Claude Code"*

---

## Sessions

Persistent memory across conversations. Sessions are stored as JSON files locally.

### grok-session-create

Create a new named session.

```
Parameters:
| Name | Type | Required | Description |
|------|------|----------|-------------|
| name | string | Yes | Session name |
| model | string | No | Model to use |
| system_prompt | string | No | Session-wide system prompt |
```

### grok-session-chat

Continue a conversation in an existing session.

```
Parameters:
| Name | Type | Required | Description |
|------|------|----------|-------------|
| session_id | string | Yes | Session ID from create |
| message | string | Yes | Message to send |
| model | string | No | Model to use |
```

### grok-session-list

List all active sessions.

```
Parameters: none
```

### grok-session-get

Get full history of a session.

```
Parameters:
| Name | Type | Required | Description |
|------|------|----------|-------------|
| session_id | string | Yes | Session ID |
```

### grok-session-delete

Delete a session.

```
Parameters:
| Name | Type | Required | Description |
|------|------|----------|-------------|
| session_id | string | Yes | Session ID |
```

---

## Chains

Multi-step research workflows. Claude calls one tool, Grok executes multiple steps.

### grok-chain-research

Deep research on a topic: search → analyze → synthesize.

```
Parameters:
| Name | Type | Required | Description |
|------|------|----------|-------------|
| topic | string | Yes | Research topic |
| model | string | No | Model to use |
```

Example: *"Research the current state of MCP adoption in AI tools"*

### grok-chain-search-summarize

Search the web and return a structured summary.

```
Parameters:
| Name | Type | Required | Description |
|------|------|----------|-------------|
| query | string | Yes | Search query |
| model | string | No | Model to use |
```

### grok-chain-debug

Debug a problem: analyze → search for solutions → recommend fix.

```
Parameters:
| Name | Type | Required | Description |
|------|------|----------|-------------|
| problem | string | Yes | Problem description |
| model | string | No | Model to use |
```

Example: *"Debug why my httpx async client times out after 30 seconds"*

---

## Media

### grok-image-generate

Generate images using Grok's image models.

```
Parameters:
| Name | Type | Required | Description |
|------|------|----------|-------------|
| prompt | string | Yes | Image description |
| model | string | No | Image model to use |
| n | integer | No | Number of images (default: 1) |
```

Example: *"Generate a logo for a developer tool called xBridge"*

### grok-image-edit

Edit an existing image with a text prompt.

```
Parameters:
| Name | Type | Required | Description |
|------|------|----------|-------------|
| prompt | string | Yes | Edit instructions |
| image_url | string | Yes | URL of image to edit |
| model | string | No | Image model to use |
```

### grok-image-models

List available image generation models.

```
Parameters: none
```

### grok-video-generate

Generate short videos (up to 15 seconds).

```
Parameters:
| Name | Type | Required | Description |
|------|------|----------|-------------|
| prompt | string | Yes | Video description |
| model | string | No | Video model to use |
```

Example: *"Generate a 15-second cinematic intro for xBridge MCP"*

---

## Documentation

Access xAI's official documentation.

### grok-docs-list

List available documentation sections.

```
Parameters: none
```

### grok-docs-search

Search the xAI documentation.

```
Parameters:
| Name | Type | Required | Description |
|------|------|----------|-------------|
| query | string | Yes | Search query |
```

### grok-docs-get

Get a specific documentation page.

```
Parameters:
| Name | Type | Required | Description |
|------|------|----------|-------------|
| path | string | Yes | Documentation path |
```

---

## Quick Reference

```
| Tool | Category | One-liner |
|------|----------|-----------|
| grok-chat | Chat | Talk to Grok |
| grok-models | Chat | List available models |
| grok-web-search | Search | Live web search |
| grok-x-search | Search | Real-time X/Twitter search |
| grok-session-create | Sessions | Start persistent session |
| grok-session-chat | Sessions | Continue session |
| grok-session-list | Sessions | List all sessions |
| grok-session-get | Sessions | Get session history |
| grok-session-delete | Sessions | Delete a session |
| grok-chain-research | Chains | Deep multi-step research |
| grok-chain-search-summarize | Chains | Search + summarize |
| grok-chain-debug | Chains | Debug with web search |
| grok-image-generate | Media | Create images |
| grok-image-edit | Media | Edit existing images |
| grok-image-models | Media | List image models |
| grok-video-generate | Media | Create short videos |
| grok-docs-list | Docs | List doc sections |
| grok-docs-search | Docs | Search docs |
| grok-docs-get | Docs | Get doc page |
```
