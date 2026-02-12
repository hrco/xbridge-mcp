#!/usr/bin/env python3
"""
Run script for xBridge MCP Server

This script runs the xBridge MCP server for integration with Claude and other MCP clients.
Make sure XAI_API_KEY environment variable is set before running.
"""

import asyncio
import sys
import os

# Add the project directory to path for local development
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from xbridge_mcp.server import main

if __name__ == "__main__":
    asyncio.run(main())
