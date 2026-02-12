"""Tests for image and video generation tools."""
import pytest
import json
from unittest.mock import AsyncMock, patch, MagicMock
from mcp.types import TextContent, ImageContent, CallToolResult

from grok_mcp_server.server import (
    handle_image_generate,
    handle_image_edit,
    handle_image_models,
    handle_video_generate,
    _format_image_response,
)


class TestImageGenerate:
    """Tests for grok-image-generate handler."""

    @pytest.mark.asyncio
    async def test_missing_prompt_returns_error(self):
        result = await handle_image_generate({})
        assert result.isError is True
        assert "prompt" in result.content[0].text.lower()

    @pytest.mark.asyncio
    @patch("grok_mcp_server.server.make_image_request")
    async def test_basic_generation_url_format(self, mock_request):
        mock_request.return_value = {
            "url": "https://example.com/image.jpg",
            "model": "grok-imagine-image",
            "respect_moderation": True,
        }
        result = await handle_image_generate({
            "prompt": "A cat",
            "response_format": "url",
        })
        assert not result.isError
        assert any("https://example.com/image.jpg" in c.text for c in result.content if hasattr(c, "text"))
        mock_request.assert_called_once()

    @pytest.mark.asyncio
    @patch("grok_mcp_server.server.make_image_request")
    async def test_basic_generation_b64_format(self, mock_request):
        mock_request.return_value = {
            "image": "iVBORw0KGgoAAAANSUhEUg==",
            "model": "grok-imagine-image",
            "respect_moderation": True,
        }
        result = await handle_image_generate({
            "prompt": "A cat",
            "response_format": "b64_json",
        })
        assert not result.isError
        image_contents = [c for c in result.content if getattr(c, "type", "") == "image"]
        assert len(image_contents) >= 1

    @pytest.mark.asyncio
    @patch("grok_mcp_server.server.make_image_request")
    async def test_batch_generation(self, mock_request):
        mock_request.return_value = [
            {"url": "https://example.com/1.jpg", "model": "grok-imagine-image", "respect_moderation": True},
            {"url": "https://example.com/2.jpg", "model": "grok-imagine-image", "respect_moderation": True},
            {"url": "https://example.com/3.jpg", "model": "grok-imagine-image", "respect_moderation": True},
        ]
        result = await handle_image_generate({
            "prompt": "A cat",
            "n": 3,
            "response_format": "url",
        })
        assert not result.isError
        full_text = " ".join(c.text for c in result.content if hasattr(c, "text"))
        assert "3 image(s)" in full_text

    @pytest.mark.asyncio
    @patch("grok_mcp_server.server.make_image_request")
    async def test_moderation_blocked(self, mock_request):
        mock_request.return_value = {
            "url": "",
            "model": "grok-imagine-image",
            "respect_moderation": False,
        }
        result = await handle_image_generate({
            "prompt": "something",
            "response_format": "url",
        })
        full_text = " ".join(c.text for c in result.content if hasattr(c, "text"))
        assert "moderation" in full_text.lower()

    @pytest.mark.asyncio
    @patch("grok_mcp_server.server.make_image_request")
    async def test_custom_model_and_aspect_ratio(self, mock_request):
        mock_request.return_value = {
            "url": "https://example.com/image.jpg",
            "model": "grok-imagine-image-pro",
            "respect_moderation": True,
        }
        await handle_image_generate({
            "prompt": "A cat",
            "model": "grok-imagine-image-pro",
            "aspect_ratio": "16:9",
            "response_format": "url",
        })
        mock_request.assert_called_once_with(
            endpoint="generations",
            prompt="A cat",
            model="grok-imagine-image-pro",
            n=1,
            aspect_ratio="16:9",
            response_format="url",
        )


class TestImageEdit:
    """Tests for grok-image-edit handler."""

    @pytest.mark.asyncio
    async def test_missing_prompt_returns_error(self):
        result = await handle_image_edit({"image_url": "https://example.com/img.jpg"})
        assert result.isError is True

    @pytest.mark.asyncio
    async def test_missing_image_url_returns_error(self):
        result = await handle_image_edit({"prompt": "Make it blue"})
        assert result.isError is True

    @pytest.mark.asyncio
    @patch("grok_mcp_server.server.make_image_request")
    async def test_basic_edit(self, mock_request):
        mock_request.return_value = {
            "url": "https://example.com/edited.jpg",
            "model": "grok-imagine-image",
            "respect_moderation": True,
        }
        result = await handle_image_edit({
            "prompt": "Make it an oil painting",
            "image_url": "https://example.com/source.jpg",
            "response_format": "url",
        })
        assert not result.isError
        mock_request.assert_called_once_with(
            endpoint="edits",
            prompt="Make it an oil painting",
            model="grok-imagine-image",
            n=1,
            response_format="url",
            image_url="https://example.com/source.jpg",
        )


class TestImageModels:
    """Tests for grok-image-models handler."""

    @pytest.mark.asyncio
    async def test_returns_model_info(self):
        result = await handle_image_models({})
        assert not result.isError
        text = result.content[0].text
        assert "grok-imagine-image" in text
        assert "grok-imagine-image-pro" in text
        assert "grok-imagine-video" in text
        assert "$0.02" in text


class TestVideoGenerate:
    """Tests for grok-video-generate handler."""

    @pytest.mark.asyncio
    async def test_missing_prompt_returns_error(self):
        result = await handle_video_generate({})
        assert result.isError is True

    @pytest.mark.asyncio
    @patch("grok_mcp_server.server.make_video_request")
    async def test_basic_text_to_video(self, mock_request):
        mock_request.return_value = {
            "status": "done",
            "video": {
                "url": "https://vidgen.x.ai/video.mp4",
                "duration": 5,
                "respect_moderation": True,
            },
            "model": "grok-imagine-video",
        }
        result = await handle_video_generate({
            "prompt": "A rocket launching",
            "duration": 5,
        })
        assert not result.isError
        full_text = " ".join(c.text for c in result.content if hasattr(c, "text"))
        assert "video.mp4" in full_text
        assert "text-to-video" in full_text

    @pytest.mark.asyncio
    @patch("grok_mcp_server.server.make_video_request")
    async def test_timeout_returns_error(self, mock_request):
        mock_request.side_effect = TimeoutError("Timed out")
        result = await handle_video_generate({"prompt": "Something"})
        assert result.isError is True
        assert "timed out" in result.content[0].text.lower()

    @pytest.mark.asyncio
    @patch("grok_mcp_server.server.make_video_request")
    async def test_runtime_error_returns_error(self, mock_request):
        mock_request.side_effect = RuntimeError("Expired")
        result = await handle_video_generate({"prompt": "Something"})
        assert result.isError is True
        assert "failed" in result.content[0].text.lower()

    @pytest.mark.asyncio
    @patch("grok_mcp_server.server.make_video_request")
    async def test_video_moderation_blocked(self, mock_request):
        mock_request.return_value = {
            "status": "done",
            "video": {
                "url": "",
                "duration": 0,
                "respect_moderation": False,
            },
            "model": "grok-imagine-video",
        }
        result = await handle_video_generate({"prompt": "Something"})
        full_text = " ".join(c.text for c in result.content if hasattr(c, "text"))
        assert "moderation" in full_text.lower()

    @pytest.mark.asyncio
    @patch("grok_mcp_server.server.make_video_request")
    async def test_image_to_video(self, mock_request):
        mock_request.return_value = {
            "status": "done",
            "video": {
                "url": "https://vidgen.x.ai/video.mp4",
                "duration": 5,
                "respect_moderation": True,
            },
            "model": "grok-imagine-video",
        }
        result = await handle_video_generate({
            "prompt": "Animate this image",
            "image_url": "https://example.com/photo.jpg",
        })
        assert not result.isError
        full_text = " ".join(c.text for c in result.content if hasattr(c, "text"))
        assert "image-to-video" in full_text


class TestFormatImageResponse:
    """Tests for the _format_image_response helper."""

    def test_single_url_response(self):
        response = {
            "url": "https://example.com/image.jpg",
            "model": "grok-imagine-image",
            "respect_moderation": True,
        }
        result = _format_image_response(response, "A cat", "grok-imagine-image", 1, "url")
        texts = [c.text for c in result.content if hasattr(c, "text")]
        assert any("https://example.com/image.jpg" in t for t in texts)

    def test_batch_url_response(self):
        response = [
            {"url": "https://example.com/1.jpg", "model": "grok-imagine-image", "respect_moderation": True},
            {"url": "https://example.com/2.jpg", "model": "grok-imagine-image", "respect_moderation": True},
        ]
        result = _format_image_response(response, "Cats", "grok-imagine-image", 2, "url")
        texts = " ".join(c.text for c in result.content if hasattr(c, "text"))
        assert "2 image(s)" in texts
        assert "Image 1/2" in texts
        assert "Image 2/2" in texts

    def test_b64_response_returns_image_content(self):
        response = {
            "image": "iVBORw0KGgoAAAANSUhEUg==",
            "model": "grok-imagine-image",
            "respect_moderation": True,
        }
        result = _format_image_response(response, "A cat", "grok-imagine-image", 1, "b64_json")
        image_contents = [c for c in result.content if isinstance(c, ImageContent)]
        assert len(image_contents) == 1
        assert image_contents[0].data == "iVBORw0KGgoAAAANSUhEUg=="

    def test_moderation_blocked_response(self):
        response = {
            "url": "",
            "model": "grok-imagine-image",
            "respect_moderation": False,
        }
        result = _format_image_response(response, "test", "grok-imagine-image", 1, "url")
        texts = " ".join(c.text for c in result.content if hasattr(c, "text"))
        assert "moderation" in texts.lower()

    def test_fallback_raw_response(self):
        response = {
            "model": "grok-imagine-image",
            "respect_moderation": True,
            "unknown_field": "data",
        }
        result = _format_image_response(response, "test", "grok-imagine-image", 1, "url")
        texts = " ".join(c.text for c in result.content if hasattr(c, "text"))
        assert "unknown_field" in texts
