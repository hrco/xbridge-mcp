"""xBridge Cloud: hosted Streamable HTTP MCP endpoint + licensing routes."""
import contextlib
import json
import os

import uvicorn
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from starlette.applications import Starlette
from starlette.datastructures import Headers
from starlette.responses import JSONResponse

from .cloud_auth import authorize
from .http_server import revoked_keys, routes
from .server import server

MAX_BODY = 1_000_000


def _counts_call(body: bytes) -> bool:
    try:
        msg = json.loads(body)
    except ValueError:
        return False
    msgs = msg if isinstance(msg, list) else [msg]
    return any(isinstance(m, dict) and m.get("method") == "tools/call" for m in msgs)


def build_app():
    manager = StreamableHTTPSessionManager(app=server, stateless=True, json_response=True)

    @contextlib.asynccontextmanager
    async def lifespan(_app):
        async with manager.run():
            yield

    site = Starlette(routes=routes, lifespan=lifespan)

    async def mcp_endpoint(scope, receive, send):
        body = b""
        more = True
        while more:
            message = await receive()
            body += message.get("body", b"")
            more = message.get("more_body", False)
            if len(body) > MAX_BODY:
                await JSONResponse({"error": "request too large"}, status_code=413)(scope, receive, send)
                return

        counts = scope["method"] == "POST" and _counts_call(body)
        result = authorize(Headers(scope=scope), revoked_keys(), counts)
        if not result.ok:
            await JSONResponse({"error": result.error}, status_code=result.status)(scope, receive, send)
            return

        replayed = False

        async def replay():
            nonlocal replayed
            if not replayed:
                replayed = True
                return {"type": "http.request", "body": body, "more_body": False}
            return await receive()

        await manager.handle_request(scope, replay, send)

    async def app(scope, receive, send):
        if scope["type"] == "http" and scope["path"].rstrip("/") == "/mcp":
            await mcp_endpoint(scope, receive, send)
        else:
            await site(scope, receive, send)

    return app


def main():
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8787"))
    uvicorn.run(build_app(), host=host, port=port, log_level="info", proxy_headers=True)


if __name__ == "__main__":
    main()