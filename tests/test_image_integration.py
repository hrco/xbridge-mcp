"""Integration tests for image generation (requires XAI_API_KEY)."""
import os
import pytest

pytestmark = pytest.mark.skipif(
    not os.environ.get("XAI_API_KEY"),
    reason="XAI_API_KEY not set"
)


class TestImageGenerationIntegration:

    @pytest.mark.asyncio
    async def test_generate_single_image_url(self):
        from grok_mcp_server.server import handle_image_generate
        result = await handle_image_generate({
            "prompt": "A simple red circle on white background",
            "model": "grok-imagine-image",
            "n": 1,
            "response_format": "url",
        })
        assert not result.isError
        texts = " ".join(c.text for c in result.content if hasattr(c, "text"))
        assert "http" in texts

    @pytest.mark.asyncio
    async def test_generate_single_image_base64(self):
        from grok_mcp_server.server import handle_image_generate
        result = await handle_image_generate({
            "prompt": "A blue square",
            "model": "grok-imagine-image",
            "n": 1,
            "response_format": "b64_json",
        })
        assert not result.isError
        image_contents = [c for c in result.content if getattr(c, "type", "") == "image"]
        assert len(image_contents) >= 1

    @pytest.mark.asyncio
    async def test_image_models_returns_info(self):
        from grok_mcp_server.server import handle_image_models
        result = await handle_image_models({})
        assert not result.isError
        assert "grok-imagine-image" in result.content[0].text
