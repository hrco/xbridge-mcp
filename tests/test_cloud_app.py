import importlib
import json

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from starlette.testclient import TestClient

from xbridge_mcp import tokenizer

XAI = "xai-secret-123"
MCP_HEADERS = {"Accept": "application/json, text/event-stream", "Content-Type": "application/json"}


@pytest.fixture
def env(monkeypatch, tmp_path):
    priv = Ed25519PrivateKey.generate()
    monkeypatch.setattr(tokenizer, "_public_key", priv.public_key())
    monkeypatch.setenv("XBRIDGE_DB_PATH", str(tmp_path))
    from xbridge_mcp import http_server, cloud
    importlib.reload(http_server)
    importlib.reload(cloud)
    with TestClient(cloud.build_app()) as client:
        yield client, (lambda tier: tokenizer.generate_key("u@x.co", tier, 30, priv))


def rpc(method, id_=1, params=None):
    return json.dumps({"jsonrpc": "2.0", "id": id_, "method": method, "params": params or {}})


INIT = {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "t", "version": "1"}}


def post(client, body, key=None, xai=XAI):
    headers = dict(MCP_HEADERS)
    if key:
        headers["Authorization"] = f"Bearer {key}"
    if xai:
        headers["X-XAI-Key"] = xai
    return client.post("/mcp", content=body, headers=headers)


def test_health_route_still_served(env):
    client, _ = env
    assert client.get("/health").status_code == 200


def test_mcp_without_key_401(env):
    client, _ = env
    r = post(client, rpc("initialize", params=INIT))
    assert r.status_code == 401 and "error" in r.json()


def test_initialize_with_pro_key(env):
    client, sign = env
    r = post(client, rpc("initialize", params=INIT), key=sign("pro"))
    assert r.status_code == 200
    assert r.json()["result"]["serverInfo"]["name"] == "xbridge-mcp"


def test_tools_list_has_all_tools(env):
    client, sign = env
    r = post(client, rpc("tools/list"), key=sign("pro"))
    assert r.status_code == 200
    names = {t["name"] for t in r.json()["result"]["tools"]}
    assert "grok-chat" in names and len(names) >= 21


def test_handshake_does_not_count(env):
    client, sign = env
    k = sign("free")
    for i in range(60):
        assert post(client, rpc("tools/list", id_=i), key=k).status_code == 200


def test_free_tier_51st_tool_call_429(env, monkeypatch):
    async def _fake(arguments):
        from mcp.types import CallToolResult, TextContent
        return CallToolResult(content=[TextContent(type="text", text="ok")])
    monkeypatch.setattr("xbridge_mcp.server.handle_grok_models", _fake)
    client, sign = env
    k = sign("free")
    call = rpc("tools/call", params={"name": "grok-models", "arguments": {}})
    # grok-models hits xAI; the call may error inside the tool, but auth must pass 50 times.
    for _ in range(50):
        assert post(client, call, key=k).status_code != 429
    assert post(client, call, key=k).status_code == 429


def test_revoked_key_403(env, monkeypatch):
    client, sign = env
    k = sign("pro")
    from xbridge_mcp import cloud
    monkeypatch.setattr(cloud, "revoked_keys", lambda: {k})
    assert post(client, rpc("tools/list"), key=k).status_code == 403


def test_garbage_body_is_not_500(env):
    client, sign = env
    for body in ("not json", "[]", json.dumps([json.loads(rpc("tools/list"))])):
        assert post(client, body, key=sign("pro")).status_code < 500


def test_xai_key_not_in_responses(env):
    client, sign = env
    for r in (post(client, rpc("tools/list")), post(client, rpc("tools/list"), key=sign("pro"), xai="sk-x"),
              post(client, rpc("tools/list"), key=sign("pro"))):
        assert XAI not in r.text and "sk-x" not in r.text