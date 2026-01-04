# Contributing to Grok MCP Server

Thank you for your interest in contributing to Grok MCP Server! This document provides guidelines and instructions for contributing.

## Code of Conduct

By participating in this project, you agree to maintain a respectful and inclusive environment for all contributors.

## How to Contribute

### Reporting Bugs

If you find a bug, please create an issue with:
- A clear, descriptive title
- Steps to reproduce the issue
- Expected behavior
- Actual behavior
- Your environment (OS, Python version, etc.)
- Any relevant logs or error messages

### Suggesting Enhancements

Enhancement suggestions are welcome! Please create an issue with:
- A clear, descriptive title
- Detailed description of the proposed enhancement
- Use cases and benefits
- Any implementation ideas you may have

### Pull Requests

1. **Fork the repository** and create your branch from `main`
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes**
   - Write clear, readable code
   - Follow the existing code style
   - Add comments for complex logic
   - Update documentation as needed

3. **Test your changes**
   ```bash
   # Install dev dependencies
   pip install -e ".[dev]"

   # Run tests
   pytest
   ```

4. **Commit your changes**
   - Use clear, descriptive commit messages
   - Reference issue numbers if applicable
   ```bash
   git commit -m "feat: add new session export feature (#123)"
   ```

5. **Push to your fork** and submit a pull request
   ```bash
   git push origin feature/your-feature-name
   ```

### Commit Message Guidelines

We follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:

- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation changes
- `style:` Code style changes (formatting, etc.)
- `refactor:` Code refactoring
- `test:` Adding or updating tests
- `chore:` Maintenance tasks

Example:
```
feat: add support for streaming chat responses
fix: resolve session persistence issue
docs: update installation instructions
```

## Development Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/grok-mcp-server.git
   cd grok-mcp-server
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install in development mode**
   ```bash
   pip install -e ".[dev]"
   ```

4. **Set up your environment**
   ```bash
   cp .env.example .env
   # Edit .env and add your XAI_API_KEY
   ```

## Code Style

- Follow [PEP 8](https://pep8.org/) style guide
- Use meaningful variable and function names
- Keep functions focused and modular
- Maximum line length: 100 characters
- Use type hints where appropriate

## Testing

- Write tests for new features
- Ensure all tests pass before submitting PR
- Aim for high test coverage
- Test edge cases and error conditions

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=grok_mcp_server

# Run specific test file
pytest tests/test_session.py
```

## Documentation

- Update README.md if adding new features
- Add docstrings to new functions and classes
- Include usage examples for new tools
- Update CHANGELOG.md for notable changes

## Project Structure

```
grok-mcp-server/
├── grok_mcp_server/      # Main package
│   ├── server.py         # MCP server and tools
│   ├── session_manager.py # Session management
│   └── tool_chains.py    # Tool chaining
├── tests/                # Test files
├── docs/                 # Documentation
├── README.md
├── CONTRIBUTING.md
├── LICENSE
└── pyproject.toml
```

## Questions?

If you have questions about contributing, feel free to:
- Open an issue for discussion
- Reach out to the maintainers
- Check existing issues and pull requests

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

Thank you for contributing to Grok MCP Server!
