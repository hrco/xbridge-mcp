# Grok MCP Server

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

MCP Server for xAI Grok API integration with advanced features including chat, web search, X/Twitter search, session management, and tool chaining.

## Features

### Core Capabilities
- **Chat with Grok models**: grok-4, grok-4-1-fast, grok-3, grok-2, and more
- **Web search**: Intelligent web search with domain filtering and image understanding
- **X/Twitter search**: Search X/Twitter with handle filtering, date ranges, and media understanding

### Advanced Features
- **Session Management**: Persistent conversation history across interactions
- **Tool Chaining**: Multi-step workflows that combine search → summarize, research, and debug operations
- **Context Retention**: Maintain conversation context across multiple tool calls

## Installation

### Prerequisites
- Python 3.10 or higher
- xAI API key ([Get one here](https://x.ai/api))

### Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/grok-mcp-server.git
   cd grok-mcp-server
   ```

2. Install the package:
   ```bash
   pip install -e .
   ```

3. Set your xAI API key:
   ```bash
   export XAI_API_KEY=REDACTED
   ```

## Usage

### Starting the Server

Run the MCP server:
```bash
python run_server.py
```

Or use the installed command:
```bash
grok-mcp
```

### Available Tools

#### Basic Tools
- `grok-chat`: Send messages to Grok
- `grok-web-search`: Search the web
- `grok-x-search`: Search X/Twitter
- `grok-models`: List available models

#### Session Management Tools
- `grok-session-create`: Create a new conversation session
- `grok-session-list`: List all active sessions
- `grok-session-get`: Get session details and history
- `grok-session-delete`: Delete a session
- `grok-session-chat`: Chat within a session (auto-maintains context)

#### Tool Chaining
- `grok-chain-search-summarize`: Search and summarize results automatically
- `grok-chain-research`: Multi-source research (web + X) with synthesis
- `grok-chain-debug`: Debug workflow (search X for issues → generate fix)

## Examples

### Basic Chat
```python
from grok_mcp_server import grok_chat

response = grok_chat(
    message="What is quantum computing?",
    model="grok-4-1-fast"
)
```

### Session-based Conversation
```python
# Create session
session_id = grok_session_create(name="Research Session")

# Chat maintains context automatically
grok_session_chat(session_id, "What is quantum computing?")
grok_session_chat(session_id, "How is it used in cryptography?")  # Knows context

# View history
grok_session_get(session_id)
```

### Search and Summarize
```python
# One tool call does: search web → summarize findings
grok_chain_search_summarize(
    query="Latest AI developments December 2025",
    search_type="web",
    summary_instructions="Provide 5 key bullet points"
)
```

### Multi-Source Research
```python
# Searches web + X, then synthesizes comprehensive report
grok_chain_research(
    topic="xAI Grok API capabilities",
    model="grok-4"
)
```

### Debug Workflow
```python
# Searches X for similar issues → generates fix
grok_chain_debug(
    error_message="ModuleNotFoundError: No module named 'mcp'",
    tech_stack="Python 3.13"
)
```

## Architecture

```
grok-mcp-server/
├── grok_mcp_server/
│   ├── __init__.py
│   ├── server.py           # Main MCP server with all tools
│   ├── session_manager.py  # Persistent session storage
│   └── tool_chains.py      # Composable tool chain workflows
├── pyproject.toml
├── run_server.py
└── README.md
```

Sessions are stored in `.grok_sessions/` as JSON files for persistence across restarts.

## Configuration

The server uses environment variables for configuration:

- `XAI_API_KEY` (required): Your xAI API key

## Development

### Running Tests

```bash
pip install -e ".[dev]"
pytest
```

### Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Built with the [Model Context Protocol](https://modelcontextprotocol.io/)
- Powered by [xAI Grok API](https://x.ai/api)

## Support

If you encounter any issues or have questions:
- Open an issue on [GitHub](https://github.com/yourusername/grok-mcp-server/issues)
- Check the [documentation](https://github.com/yourusername/grok-mcp-server/wiki)

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for release history.
