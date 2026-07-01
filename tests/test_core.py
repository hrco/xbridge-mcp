"""
Tests for core server functionality:
  - get_api_key()
  - extract_response_text()
  - make_grok_request()
  - handle_grok_chat / handle_grok_web_search / handle_grok_x_search
"""
import pytest
import httpx
from unittest.mock import AsyncMock, MagicMock, patch

from xbridge_mcp.server import (
    AVAILABLE_MODELS,
    DEFAULT_MODEL,
    extract_response_text,
    get_api_key,
    handle_grok_chat,
    handle_grok_models,
    handle_grok_web_search,
    handle_grok_x_search,
    make_grok_request,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_http_client(response_data: dict) -> MagicMock:
    """Return a mock async-context-manager httpx client whose POST returns response_data."""
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = response_data

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.post = AsyncMock(return_value=mock_response)
    return mock_client


def _grok_response(text: str) -> dict:
    """Minimal valid Grok API response containing one assistant message."""
    return {
        "output": [
            {
                "type": "message",
                "role": "assistant",
                "content": [{"type": "output_text", "text": text}],
            }
        ]
    }


# ---------------------------------------------------------------------------
# get_api_key
# ---------------------------------------------------------------------------

class TestGetApiKey:
    def test_returns_key_when_set(self, monkeypatch):
        monkeypatch.setenv("XAI_API_KEY", "sk-test-123")
        assert get_api_key() == "sk-test-123"

    def test_raises_value_error_when_missing(self, monkeypatch):
        monkeypatch.delenv("XAI_API_KEY", raising=False)
        with pytest.raises(ValueError, match="XAI_API_KEY"):
            get_api_key()


# ---------------------------------------------------------------------------
# extract_response_text
# ---------------------------------------------------------------------------

class TestExtractResponseText:
    """Tests for the nested response parser — covers all documented paths."""

    def test_extracts_output_text_from_assistant_message(self):
        response = _grok_response("Hello world")
        assert extract_response_text(response) == "Hello world"

    def test_joins_multiple_output_text_items(self):
        response = {
            "output": [
                {
                    "type": "message",
                    "role": "assistant",
                    "content": [
                        {"type": "output_text", "text": "Line 1"},
                        {"type": "output_text", "text": "Line 2"},
                    ],
                }
            ]
        }
        result = extract_response_text(response)
        assert "Line 1" in result
        assert "Line 2" in result

    def test_extracts_from_content_list_with_text_type(self):
        response = {
            "output": [
                {
                    "content": [{"type": "text", "text": "alt format"}]
                }
            ]
        }
        assert extract_response_text(response) == "alt format"

    def test_extracts_from_content_as_plain_string(self):
        response = {
            "output": [
                {"content": "plain string content"}
            ]
        }
        assert extract_response_text(response) == "plain string content"

    def test_extracts_direct_text_field(self):
        response = {
            "output": [{"text": "direct text value"}]
        }
        assert extract_response_text(response) == "direct text value"

    def test_output_as_plain_string(self):
        response = {"output": "flat string output"}
        assert extract_response_text(response) == "flat string output"

    def test_fallback_to_json_when_no_output_key(self):
        response = {"model": "grok-4", "usage": {"tokens": 100}}
        result = extract_response_text(response)
        assert "grok-4" in result

    def test_empty_output_list_falls_back_to_json(self):
        response = {"output": []}
        result = extract_response_text(response)
        assert isinstance(result, str)

    def test_skips_non_assistant_messages(self):
        response = {
            "output": [
                {
                    "type": "message",
                    "role": "user",
                    "content": [{"type": "output_text", "text": "skip me"}],
                },
                {
                    "type": "message",
                    "role": "assistant",
                    "content": [{"type": "output_text", "text": "include me"}],
                },
            ]
        }
        result = extract_response_text(response)
        assert "include me" in result

    def test_ignores_non_output_text_content_types(self):
        response = {
            "output": [
                {
                    "type": "message",
                    "role": "assistant",
                    "content": [
                        {"type": "tool_call", "text": "ignored"},
                        {"type": "output_text", "text": "kept"},
                    ],
                }
            ]
        }
        result = extract_response_text(response)
        assert result == "kept"


# ---------------------------------------------------------------------------
# make_grok_request
# ---------------------------------------------------------------------------

class TestMakeGrokRequest:
    """Unit tests for the core API request builder."""

    async def test_happy_path_returns_parsed_json(self, monkeypatch):
        monkeypatch.setenv("XAI_API_KEY", "test-key")
        api_response = _grok_response("Hi")
        mock_client = _mock_http_client(api_response)

        with patch("xbridge_mcp.server.httpx.AsyncClient", return_value=mock_client):
            result = await make_grok_request(
                messages=[{"role": "user", "content": "Hello"}],
            )

        assert result == api_response

    async def test_sends_bearer_auth_header(self, monkeypatch):
        monkeypatch.setenv("XAI_API_KEY", "my-secret-key")
        mock_client = _mock_http_client({"output": []})

        with patch("xbridge_mcp.server.httpx.AsyncClient", return_value=mock_client):
            await make_grok_request(messages=[{"role": "user", "content": "hi"}])

        headers = mock_client.post.call_args[1]["headers"]
        assert headers["Authorization"] == "Bearer my-secret-key"

    async def test_sends_content_type_json(self, monkeypatch):
        monkeypatch.setenv("XAI_API_KEY", "test-key")
        mock_client = _mock_http_client({"output": []})

        with patch("xbridge_mcp.server.httpx.AsyncClient", return_value=mock_client):
            await make_grok_request(messages=[{"role": "user", "content": "hi"}])

        headers = mock_client.post.call_args[1]["headers"]
        assert headers["Content-Type"] == "application/json"

    async def test_sends_correct_model(self, monkeypatch):
        monkeypatch.setenv("XAI_API_KEY", "test-key")
        mock_client = _mock_http_client({"output": []})

        with patch("xbridge_mcp.server.httpx.AsyncClient", return_value=mock_client):
            await make_grok_request(
                messages=[{"role": "user", "content": "hi"}],
                model="grok-4",
            )

        payload = mock_client.post.call_args[1]["json"]
        assert payload["model"] == "grok-4"

    async def test_uses_default_model_when_not_specified(self, monkeypatch):
        monkeypatch.setenv("XAI_API_KEY", "test-key")
        mock_client = _mock_http_client({"output": []})

        with patch("xbridge_mcp.server.httpx.AsyncClient", return_value=mock_client):
            await make_grok_request(messages=[{"role": "user", "content": "hi"}])

        payload = mock_client.post.call_args[1]["json"]
        assert payload["model"] == DEFAULT_MODEL

    async def test_prepends_system_prompt_as_first_message(self, monkeypatch):
        monkeypatch.setenv("XAI_API_KEY", "test-key")
        mock_client = _mock_http_client({"output": []})

        with patch("xbridge_mcp.server.httpx.AsyncClient", return_value=mock_client):
            await make_grok_request(
                messages=[{"role": "user", "content": "hello"}],
                system_prompt="Be concise.",
            )

        payload = mock_client.post.call_args[1]["json"]
        input_messages = payload["input"]
        assert input_messages[0] == {"role": "system", "content": "Be concise."}
        assert input_messages[1] == {"role": "user", "content": "hello"}

    async def test_no_system_message_when_not_provided(self, monkeypatch):
        monkeypatch.setenv("XAI_API_KEY", "test-key")
        mock_client = _mock_http_client({"output": []})

        with patch("xbridge_mcp.server.httpx.AsyncClient", return_value=mock_client):
            await make_grok_request(
                messages=[{"role": "user", "content": "hello"}],
            )

        payload = mock_client.post.call_args[1]["json"]
        assert payload["input"][0]["role"] != "system"

    async def test_includes_tools_in_payload(self, monkeypatch):
        monkeypatch.setenv("XAI_API_KEY", "test-key")
        mock_client = _mock_http_client({"output": []})
        tools = [{"type": "web_search"}]

        with patch("xbridge_mcp.server.httpx.AsyncClient", return_value=mock_client):
            await make_grok_request(
                messages=[{"role": "user", "content": "search"}],
                tools=tools,
            )

        payload = mock_client.post.call_args[1]["json"]
        assert payload["tools"] == tools

    async def test_omits_tools_key_when_none(self, monkeypatch):
        monkeypatch.setenv("XAI_API_KEY", "test-key")
        mock_client = _mock_http_client({"output": []})

        with patch("xbridge_mcp.server.httpx.AsyncClient", return_value=mock_client):
            await make_grok_request(messages=[{"role": "user", "content": "hi"}])

        payload = mock_client.post.call_args[1]["json"]
        assert "tools" not in payload

    async def test_http_error_propagates(self, monkeypatch):
        monkeypatch.setenv("XAI_API_KEY", "test-key")
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "401 Unauthorized", request=MagicMock(), response=MagicMock()
        )
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch("xbridge_mcp.server.httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(httpx.HTTPStatusError):
                await make_grok_request(messages=[{"role": "user", "content": "hi"}])

    async def test_raises_on_missing_api_key(self, monkeypatch):
        monkeypatch.delenv("XAI_API_KEY", raising=False)
        with pytest.raises(ValueError, match="XAI_API_KEY"):
            await make_grok_request(messages=[{"role": "user", "content": "hi"}])


# ---------------------------------------------------------------------------
# handle_grok_chat
# ---------------------------------------------------------------------------

class TestHandleGrokChat:

    async def test_missing_message_returns_error(self):
        result = await handle_grok_chat({})
        assert result.isError is True
        assert "message" in result.content[0].text.lower()

    async def test_happy_path_returns_response_text(self, monkeypatch):
        monkeypatch.setenv("XAI_API_KEY", "test-key")
        with patch(
            "xbridge_mcp.server.make_grok_request",
            new=AsyncMock(return_value=_grok_response("Sure!")),
        ):
            result = await handle_grok_chat({"message": "Hello"})

        assert not result.isError
        assert "Sure!" in result.content[0].text

    async def test_passes_conversation_history(self, monkeypatch):
        monkeypatch.setenv("XAI_API_KEY", "test-key")
        history = [
            {"role": "user", "content": "First"},
            {"role": "assistant", "content": "Reply"},
        ]
        mock_req = AsyncMock(return_value=_grok_response("ok"))

        with patch("xbridge_mcp.server.make_grok_request", new=mock_req):
            await handle_grok_chat({"message": "Next", "conversation_history": history})

        messages = mock_req.call_args[1]["messages"]
        assert len(messages) == 3
        assert messages[-1] == {"role": "user", "content": "Next"}

    async def test_uses_specified_model(self, monkeypatch):
        monkeypatch.setenv("XAI_API_KEY", "test-key")
        mock_req = AsyncMock(return_value=_grok_response("ok"))

        with patch("xbridge_mcp.server.make_grok_request", new=mock_req):
            await handle_grok_chat({"message": "Hi", "model": "grok-4"})

        assert mock_req.call_args[1]["model"] == "grok-4"

    async def test_passes_system_prompt(self, monkeypatch):
        monkeypatch.setenv("XAI_API_KEY", "test-key")
        mock_req = AsyncMock(return_value=_grok_response("ok"))

        with patch("xbridge_mcp.server.make_grok_request", new=mock_req):
            await handle_grok_chat({"message": "Hi", "system_prompt": "Be brief."})

        assert mock_req.call_args[1]["system_prompt"] == "Be brief."

    async def test_http_error_bubbles_up(self, monkeypatch):
        monkeypatch.setenv("XAI_API_KEY", "test-key")
        with patch(
            "xbridge_mcp.server.make_grok_request",
            new=AsyncMock(side_effect=httpx.HTTPStatusError("429", request=MagicMock(), response=MagicMock())),
        ):
            with pytest.raises(httpx.HTTPStatusError):
                await handle_grok_chat({"message": "flood"})


# ---------------------------------------------------------------------------
# handle_grok_web_search
# ---------------------------------------------------------------------------

class TestHandleGrokWebSearch:

    async def test_missing_query_returns_error(self):
        result = await handle_grok_web_search({})
        assert result.isError is True
        assert "query" in result.content[0].text.lower()

    async def test_sends_web_search_tool_type(self, monkeypatch):
        monkeypatch.setenv("XAI_API_KEY", "test-key")
        mock_req = AsyncMock(return_value={"output": [{"text": "results"}]})

        with patch("xbridge_mcp.server.make_grok_request", new=mock_req):
            await handle_grok_web_search({"query": "latest AI news"})

        tools = mock_req.call_args[1]["tools"]
        assert any(t["type"] == "web_search" for t in tools)

    async def test_allowed_domains_forwarded(self, monkeypatch):
        monkeypatch.setenv("XAI_API_KEY", "test-key")
        mock_req = AsyncMock(return_value={"output": []})

        with patch("xbridge_mcp.server.make_grok_request", new=mock_req):
            await handle_grok_web_search(
                {"query": "python", "allowed_domains": ["docs.python.org"]}
            )

        web_tool = next(t for t in mock_req.call_args[1]["tools"] if t["type"] == "web_search")
        assert web_tool["allowed_domains"] == ["docs.python.org"]

    async def test_excluded_domains_forwarded(self, monkeypatch):
        monkeypatch.setenv("XAI_API_KEY", "test-key")
        mock_req = AsyncMock(return_value={"output": []})

        with patch("xbridge_mcp.server.make_grok_request", new=mock_req):
            await handle_grok_web_search(
                {"query": "test", "excluded_domains": ["pinterest.com"]}
            )

        web_tool = next(t for t in mock_req.call_args[1]["tools"] if t["type"] == "web_search")
        assert web_tool["excluded_domains"] == ["pinterest.com"]

    async def test_image_understanding_flag_set(self, monkeypatch):
        monkeypatch.setenv("XAI_API_KEY", "test-key")
        mock_req = AsyncMock(return_value={"output": []})

        with patch("xbridge_mcp.server.make_grok_request", new=mock_req):
            await handle_grok_web_search(
                {"query": "test", "enable_image_understanding": True}
            )

        web_tool = next(t for t in mock_req.call_args[1]["tools"] if t["type"] == "web_search")
        assert web_tool.get("enable_image_understanding") is True

    async def test_image_understanding_not_set_by_default(self, monkeypatch):
        monkeypatch.setenv("XAI_API_KEY", "test-key")
        mock_req = AsyncMock(return_value={"output": []})

        with patch("xbridge_mcp.server.make_grok_request", new=mock_req):
            await handle_grok_web_search({"query": "test"})

        web_tool = next(t for t in mock_req.call_args[1]["tools"] if t["type"] == "web_search")
        assert "enable_image_understanding" not in web_tool


# ---------------------------------------------------------------------------
# handle_grok_x_search
# ---------------------------------------------------------------------------

class TestHandleGrokXSearch:

    async def test_missing_query_returns_error(self):
        result = await handle_grok_x_search({})
        assert result.isError is True
        assert "query" in result.content[0].text.lower()

    async def test_sends_x_search_tool_type(self, monkeypatch):
        monkeypatch.setenv("XAI_API_KEY", "test-key")
        mock_req = AsyncMock(return_value={"output": []})

        with patch("xbridge_mcp.server.make_grok_request", new=mock_req):
            await handle_grok_x_search({"query": "xBridge"})

        tools = mock_req.call_args[1]["tools"]
        assert any(t["type"] == "x_search" for t in tools)

    async def test_allowed_x_handles_forwarded(self, monkeypatch):
        monkeypatch.setenv("XAI_API_KEY", "test-key")
        mock_req = AsyncMock(return_value={"output": []})

        with patch("xbridge_mcp.server.make_grok_request", new=mock_req):
            await handle_grok_x_search(
                {"query": "xBridge", "allowed_x_handles": ["elonmusk"]}
            )

        x_tool = next(t for t in mock_req.call_args[1]["tools"] if t["type"] == "x_search")
        assert x_tool["allowed_x_handles"] == ["elonmusk"]

    async def test_date_range_forwarded(self, monkeypatch):
        monkeypatch.setenv("XAI_API_KEY", "test-key")
        mock_req = AsyncMock(return_value={"output": []})

        with patch("xbridge_mcp.server.make_grok_request", new=mock_req):
            await handle_grok_x_search(
                {"query": "test", "from_date": "2024-01-01", "to_date": "2024-12-31"}
            )

        x_tool = next(t for t in mock_req.call_args[1]["tools"] if t["type"] == "x_search")
        assert x_tool["from_date"] == "2024-01-01"
        assert x_tool["to_date"] == "2024-12-31"

    async def test_excluded_handles_forwarded(self, monkeypatch):
        monkeypatch.setenv("XAI_API_KEY", "test-key")
        mock_req = AsyncMock(return_value={"output": []})

        with patch("xbridge_mcp.server.make_grok_request", new=mock_req):
            await handle_grok_x_search(
                {"query": "test", "excluded_x_handles": ["spam_bot"]}
            )

        x_tool = next(t for t in mock_req.call_args[1]["tools"] if t["type"] == "x_search")
        assert x_tool["excluded_x_handles"] == ["spam_bot"]

    async def test_video_understanding_flag(self, monkeypatch):
        monkeypatch.setenv("XAI_API_KEY", "test-key")
        mock_req = AsyncMock(return_value={"output": []})

        with patch("xbridge_mcp.server.make_grok_request", new=mock_req):
            await handle_grok_x_search(
                {"query": "test", "enable_video_understanding": True}
            )

        x_tool = next(t for t in mock_req.call_args[1]["tools"] if t["type"] == "x_search")
        assert x_tool.get("enable_video_understanding") is True


class TestGrokModels:
    """Tests for handle_grok_models / AVAILABLE_MODELS (xAI 2026-07 Safe-refresh, issue #18)."""

    def test_grok_build_0_1_listed(self):
        assert "grok-build-0.1" in AVAILABLE_MODELS

    @pytest.mark.asyncio
    async def test_grok_build_0_1_in_models_info(self):
        result = await handle_grok_models({})
        text = result.content[0].text
        assert "grok-build-0.1" in text

    @pytest.mark.asyncio
    async def test_4_20_family_context_and_pricing_current(self):
        result = await handle_grok_models({})
        text = result.content[0].text
        # 4.20 family is 1M context / $1.25 x $2.50, per xAI's current pricing docs -
        # not the stale 2M / $2.00 x $6.00 figures.
        section = text.split("## Flagship Models")[0]
        assert "grok-4.20-0309-reasoning" in section
        assert "2M tokens" not in section
        assert "$2.00 ($0.20 cached) / $6.00" not in section
        assert "$1.25/$2.50" in section
