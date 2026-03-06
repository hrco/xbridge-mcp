import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch

from xbridge_mcp.server import _call_docs_mcp


@pytest.mark.asyncio
async def test_call_docs_mcp_extracts_text():
    """_call_docs_mcp should POST JSON-RPC and return text from result.content[0].text."""
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {
        "jsonrpc": "2.0",
        "id": 1,
        "result": {
            "content": [{"type": "text", "text": "page1\npage2"}],
            "isError": False,
        },
    }

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.post = AsyncMock(return_value=mock_response)

    with patch("xbridge_mcp.server.httpx.AsyncClient", return_value=mock_client):
        result = await _call_docs_mcp("list_doc_pages", {})

    assert result == "page1\npage2"
    mock_client.post.assert_called_once()
    call_args = mock_client.post.call_args
    assert call_args[0][0] == "https://docs.x.ai/api/mcp"
    body = call_args[1]["json"]
    assert body["method"] == "tools/call"
    assert body["params"]["name"] == "list_doc_pages"


@pytest.mark.asyncio
async def test_call_docs_mcp_passes_arguments():
    """_call_docs_mcp should forward arguments to the JSON-RPC payload."""
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {
        "result": {"content": [{"type": "text", "text": "results"}]}
    }

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.post = AsyncMock(return_value=mock_response)

    with patch("xbridge_mcp.server.httpx.AsyncClient", return_value=mock_client):
        await _call_docs_mcp("search_docs", {"query": "grok models", "limit": 3})

    body = mock_client.post.call_args[1]["json"]
    assert body["params"]["arguments"] == {"query": "grok models", "limit": 3}


from xbridge_mcp.server import handle_docs_list
from mcp.types import CallToolResult


@pytest.mark.asyncio
async def test_handle_docs_list_returns_text():
    """grok-docs-list should return a CallToolResult with text content."""
    with patch("xbridge_mcp.server._call_docs_mcp", new=AsyncMock(return_value="page-a\npage-b")):
        result = await handle_docs_list({})

    assert isinstance(result, CallToolResult)
    assert not result.isError
    assert "page-a" in result.content[0].text


from xbridge_mcp.server import handle_docs_search


@pytest.mark.asyncio
async def test_handle_docs_search_passes_query_and_limit():
    mock_fn = AsyncMock(return_value="result-a\nresult-b")
    with patch("xbridge_mcp.server._call_docs_mcp", new=mock_fn):
        result = await handle_docs_search({"query": "models", "limit": 3})

    assert isinstance(result, CallToolResult)
    assert not result.isError
    mock_fn.assert_called_once_with("search_docs", {"query": "models", "limit": 3})


@pytest.mark.asyncio
async def test_handle_docs_search_requires_query():
    result = await handle_docs_search({})
    assert result.isError
    assert "query" in result.content[0].text.lower()


from xbridge_mcp.server import handle_docs_get


@pytest.mark.asyncio
async def test_handle_docs_get_passes_slug():
    mock_fn = AsyncMock(return_value="# Quickstart\nContent here")
    with patch("xbridge_mcp.server._call_docs_mcp", new=mock_fn):
        result = await handle_docs_get({"slug": "quickstart"})

    assert isinstance(result, CallToolResult)
    assert not result.isError
    mock_fn.assert_called_once_with("get_doc_page", {"slug": "quickstart"})


@pytest.mark.asyncio
async def test_handle_docs_get_requires_slug():
    result = await handle_docs_get({})
    assert result.isError
    assert "slug" in result.content[0].text.lower()
