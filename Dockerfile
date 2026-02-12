FROM python:3.12-slim AS base

LABEL maintainer="hrco"
LABEL description="xBridge MCP - xAI Grok API tools for Model Context Protocol"
LABEL version="2.1.0"

WORKDIR /app

# Install dependencies first (cache layer)
COPY pyproject.toml .
RUN pip install --no-cache-dir mcp>=1.0.0 httpx>=0.27.0

# Copy application code
COPY xbridge_mcp/ ./xbridge_mcp/
COPY run_server.py .

# Install package
RUN pip install --no-cache-dir -e .

# Health check: verify the package imports correctly
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "from xbridge_mcp.server import server; print('ok')" || exit 1

# MCP servers communicate via stdio
ENV PYTHONUNBUFFERED=1

# Run the server
CMD ["xbridge-mcp"]
