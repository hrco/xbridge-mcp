"""Tests for speech-to-text tools."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from xbridge_mcp.server import (
    handle_grok_stt,
    make_stt_request,
    STT_API_BASE,
)


class TestGrokSTT:
    """Tests for grok-stt handler."""

    @pytest.mark.asyncio
    async def test_missing_audio_url_returns_error(self):
        result = await handle_grok_stt({})
        assert result.isError is True
        assert "audio_url" in result.content[0].text.lower()

    @pytest.mark.asyncio
    @patch("xbridge_mcp.server.make_stt_request")
    async def test_basic_transcription(self, mock_request):
        mock_request.return_value = {
            "text": "Hello world",
            "language": "en",
            "duration": 2.5,
            "words": [],
        }
        result = await handle_grok_stt({"audio_url": "https://example.com/audio.mp3"})
        assert not result.isError
        full_text = " ".join(c.text for c in result.content if hasattr(c, "text"))
        assert "Hello world" in full_text
        assert "en" in full_text

    @pytest.mark.asyncio
    @patch("xbridge_mcp.server.make_stt_request")
    async def test_default_args_passed_through(self, mock_request):
        mock_request.return_value = {"text": "hi", "language": "en", "duration": 1.0, "words": []}
        await handle_grok_stt({"audio_url": "https://example.com/audio.mp3"})
        mock_request.assert_called_once_with(
            audio_url="https://example.com/audio.mp3",
            language=None,
            diarize=False,
            filler_words=False,
            inverse_text_norm=False,
            multichannel=False,
            channels=None,
        )

    @pytest.mark.asyncio
    @patch("xbridge_mcp.server.make_stt_request")
    async def test_inverse_text_normalization_requires_language(self, mock_request):
        result = await handle_grok_stt({
            "audio_url": "https://example.com/audio.mp3",
            "inverse_text_normalization": True,
        })
        assert result.isError is True
        assert "language" in result.content[0].text.lower()
        mock_request.assert_not_called()

    @pytest.mark.asyncio
    @patch("xbridge_mcp.server.make_stt_request")
    async def test_inverse_text_normalization_with_language_ok(self, mock_request):
        mock_request.return_value = {"text": "hi", "language": "en", "duration": 1.0, "words": []}
        result = await handle_grok_stt({
            "audio_url": "https://example.com/audio.mp3",
            "inverse_text_normalization": True,
            "language": "en",
        })
        assert not result.isError
        mock_request.assert_called_once_with(
            audio_url="https://example.com/audio.mp3",
            language="en",
            diarize=False,
            filler_words=False,
            inverse_text_norm=True,
            multichannel=False,
            channels=None,
        )

    @pytest.mark.asyncio
    @patch("xbridge_mcp.server.make_stt_request")
    async def test_diarize_includes_speaker_table(self, mock_request):
        mock_request.return_value = {
            "text": "Hi there",
            "language": "en",
            "duration": 2.0,
            "words": [
                {"text": "Hi", "start": 0.0, "end": 0.3, "speaker": 0},
                {"text": "there", "start": 0.3, "end": 0.6, "speaker": 1},
            ],
        }
        result = await handle_grok_stt({
            "audio_url": "https://example.com/audio.mp3",
            "diarize": True,
        })
        full_text = " ".join(c.text for c in result.content if hasattr(c, "text"))
        assert "speaker 0" in full_text
        assert "speaker 1" in full_text

    @pytest.mark.asyncio
    @patch("xbridge_mcp.server.make_stt_request")
    async def test_no_diarize_or_multichannel_omits_table(self, mock_request):
        mock_request.return_value = {
            "text": "Hi there",
            "language": "en",
            "duration": 2.0,
            "words": [{"text": "Hi", "start": 0.0, "end": 0.3}],
        }
        result = await handle_grok_stt({"audio_url": "https://example.com/audio.mp3"})
        full_text = " ".join(c.text for c in result.content if hasattr(c, "text"))
        assert "Speaker/Channel" not in full_text


class TestMakeSTTRequest:
    """Tests for make_stt_request multipart payload construction."""

    def _mock_client(self, json_data):
        response = MagicMock()
        response.raise_for_status = MagicMock()
        response.json = MagicMock(return_value=json_data)

        client = MagicMock()
        client.post = AsyncMock(return_value=response)
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=False)
        return client

    @pytest.mark.asyncio
    @patch("xbridge_mcp.server.httpx.AsyncClient")
    @patch("xbridge_mcp.server.get_api_key", return_value="sk-test-123")
    async def test_url_only_sent_as_multipart_field(self, mock_key, mock_async_client):
        client = self._mock_client({"text": "hi", "language": "en", "duration": 1.0, "words": []})
        mock_async_client.return_value = client

        await make_stt_request(audio_url="https://example.com/audio.mp3")

        _, kwargs = client.post.call_args
        assert kwargs["files"]["url"] == (None, "https://example.com/audio.mp3")
        assert "language" not in kwargs["files"]
        args, _ = client.post.call_args
        assert args[0] == STT_API_BASE

    @pytest.mark.asyncio
    @patch("xbridge_mcp.server.httpx.AsyncClient")
    @patch("xbridge_mcp.server.get_api_key", return_value="sk-test-123")
    async def test_optional_fields_included_when_set(self, mock_key, mock_async_client):
        client = self._mock_client({"text": "hi", "language": "en", "duration": 1.0, "words": []})
        mock_async_client.return_value = client

        await make_stt_request(
            audio_url="https://example.com/audio.mp3",
            language="en",
            diarize=True,
            filler_words=True,
            inverse_text_norm=True,
            multichannel=True,
            channels=2,
        )

        _, kwargs = client.post.call_args
        files = kwargs["files"]
        assert files["language"] == (None, "en")
        assert files["diarize"] == (None, "true")
        assert files["filler_words"] == (None, "true")
        assert files["format"] == (None, "true")
        assert files["multichannel"] == (None, "true")
        assert files["channels"] == (None, "2")
