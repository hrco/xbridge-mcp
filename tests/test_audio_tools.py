"""Tests for text-to-speech tools."""
import pytest
from unittest.mock import patch
from mcp.types import TextContent, AudioContent

from xbridge_mcp.server import (
    handle_grok_tts,
    make_tts_request,
    TTS_VOICES,
    DEFAULT_TTS_VOICE,
)


class TestGrokTTS:
    """Tests for grok-tts handler."""

    @pytest.mark.asyncio
    async def test_missing_text_returns_error(self):
        result = await handle_grok_tts({})
        assert result.isError is True
        assert "text" in result.content[0].text.lower()

    @pytest.mark.asyncio
    @patch("xbridge_mcp.server.make_tts_request")
    async def test_basic_synthesis_returns_audio_content(self, mock_request):
        mock_request.return_value = {
            "audio": "SUQzAwAAAAAAF1RTU0U=",
            "content_type": "audio/mpeg",
            "duration": 1.23,
            "audio_timestamps": {"graph_chars": [], "graph_times": []},
        }
        result = await handle_grok_tts({"text": "Hello world"})
        assert not result.isError
        audio_contents = [c for c in result.content if isinstance(c, AudioContent)]
        assert len(audio_contents) == 1
        assert audio_contents[0].data == "SUQzAwAAAAAAF1RTU0U="
        assert audio_contents[0].mimeType == "audio/mpeg"

    @pytest.mark.asyncio
    @patch("xbridge_mcp.server.make_tts_request")
    async def test_default_voice_and_language_used(self, mock_request):
        mock_request.return_value = {
            "audio": "abc",
            "content_type": "audio/mpeg",
            "duration": 1.0,
        }
        await handle_grok_tts({"text": "Hello"})
        mock_request.assert_called_once_with(
            text="Hello",
            voice_id=DEFAULT_TTS_VOICE,
            language="auto",
            speed=1.0,
        )

    @pytest.mark.asyncio
    @patch("xbridge_mcp.server.make_tts_request")
    async def test_custom_voice_language_speed(self, mock_request):
        mock_request.return_value = {
            "audio": "abc",
            "content_type": "audio/mpeg",
            "duration": 1.0,
        }
        await handle_grok_tts({
            "text": "Bonjour",
            "voice": "ara",
            "language": "fr",
            "speed": 1.3,
        })
        mock_request.assert_called_once_with(
            text="Bonjour",
            voice_id="ara",
            language="fr",
            speed=1.3,
        )

    @pytest.mark.asyncio
    @patch("xbridge_mcp.server.make_tts_request")
    async def test_with_timestamps_includes_table(self, mock_request):
        mock_request.return_value = {
            "audio": "abc",
            "content_type": "audio/mpeg",
            "duration": 0.5,
            "audio_timestamps": {
                "graph_chars": ["H", "i"],
                "graph_times": [[0.0, 0.1], [0.1, 0.2]],
            },
        }
        result = await handle_grok_tts({"text": "Hi", "with_timestamps": True})
        assert not result.isError
        full_text = " ".join(c.text for c in result.content if hasattr(c, "text"))
        assert "Char" in full_text
        assert "`H`" in full_text
        assert "`i`" in full_text

    @pytest.mark.asyncio
    @patch("xbridge_mcp.server.make_tts_request")
    async def test_without_timestamps_omits_table(self, mock_request):
        mock_request.return_value = {
            "audio": "abc",
            "content_type": "audio/mpeg",
            "duration": 0.5,
            "audio_timestamps": {
                "graph_chars": ["H", "i"],
                "graph_times": [[0.0, 0.1], [0.1, 0.2]],
            },
        }
        result = await handle_grok_tts({"text": "Hi"})
        full_text = " ".join(c.text for c in result.content if hasattr(c, "text"))
        assert "Char" not in full_text


class TestTTSConstants:
    def test_voices_registered(self):
        assert "eve" in TTS_VOICES
        assert "ara" in TTS_VOICES
        assert "rex" in TTS_VOICES
        assert "sal" in TTS_VOICES
        assert "leo" in TTS_VOICES
        assert DEFAULT_TTS_VOICE == "eve"


class TestMakeTTSRequest:
    """Tests for make_tts_request payload construction."""

    @pytest.mark.asyncio
    @patch("xbridge_mcp.server.httpx.AsyncClient")
    @patch("xbridge_mcp.server.get_api_key", return_value="sk-test-123")
    async def test_always_requests_timestamps(self, mock_key, mock_async_client):
        from unittest.mock import AsyncMock, MagicMock

        response = MagicMock()
        response.raise_for_status = MagicMock()
        response.json = MagicMock(return_value={"audio": "abc", "content_type": "audio/mpeg", "duration": 1.0})

        client = MagicMock()
        client.post = AsyncMock(return_value=response)
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=False)
        mock_async_client.return_value = client

        await make_tts_request(text="Hello")

        _, kwargs = client.post.call_args
        assert kwargs["json"]["with_timestamps"] is True
        assert kwargs["json"]["text"] == "Hello"
        assert kwargs["json"]["voice_id"] == DEFAULT_TTS_VOICE
