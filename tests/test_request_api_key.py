from types import SimpleNamespace

import pytest
from mcp.server.lowlevel.server import request_ctx

from xbridge_mcp import server as srv


def _ctx(headers):
    return SimpleNamespace(request=SimpleNamespace(headers=headers))


def test_env_used_outside_request(monkeypatch):
    monkeypatch.setenv("XAI_API_KEY", "xai-env")
    assert srv.get_api_key() == "xai-env"


def test_header_beats_env(monkeypatch):
    monkeypatch.setenv("XAI_API_KEY", "xai-env")
    token = request_ctx.set(_ctx({"x-xai-key": "xai-header"}))
    try:
        assert srv.get_api_key() == "xai-header"
    finally:
        request_ctx.reset(token)


def test_request_without_header_falls_back_to_env(monkeypatch):
    monkeypatch.setenv("XAI_API_KEY", "xai-env")
    token = request_ctx.set(_ctx({}))
    try:
        assert srv.get_api_key() == "xai-env"
    finally:
        request_ctx.reset(token)


def test_stdio_request_has_no_http_request(monkeypatch):
    monkeypatch.setenv("XAI_API_KEY", "xai-env")
    token = request_ctx.set(SimpleNamespace(request=None))
    try:
        assert srv.get_api_key() == "xai-env"
    finally:
        request_ctx.reset(token)


def test_missing_everywhere_raises(monkeypatch):
    monkeypatch.delenv("XAI_API_KEY", raising=False)
    with pytest.raises(ValueError):
        srv.get_api_key()
