"""Auth decision for the hosted MCP endpoint. Pure: no I/O beyond the free-tier counter."""
from dataclasses import dataclass
from typing import Mapping

from .tokenizer import check_free_limit, validate_key

FREE_DAILY_CALLS = 50


@dataclass(frozen=True)
class AuthResult:
    ok: bool
    status: int
    error: str = ""
    tier: str = ""


def _deny(status: int, error: str) -> AuthResult:
    return AuthResult(ok=False, status=status, error=error)


def authorize(headers: Mapping[str, str], revoked: set[str], counts_call: bool) -> AuthResult:
    h = {k.lower(): v for k, v in headers.items()}
    auth = h.get("authorization", "")
    key = auth[7:].strip() if auth[:7].lower() == "bearer " else ""
    if not key.startswith("xbrdg_v1."):
        return _deny(401, "missing xBridge key: send Authorization: Bearer xbrdg_v1...")

    result = validate_key(key)
    if not result.get("valid"):
        return _deny(401, f"invalid xBridge key ({result.get('reason', 'unknown')})")
    if key in revoked:
        return _deny(403, "subscription ended: renew at https://xbridgemcp.com")

    xai = h.get("x-xai-key", "")
    if not xai.startswith("xai-"):
        return _deny(400, "missing X-XAI-Key header (your xAI API key, starts with xai-)")

    tier = result.get("tier", "free")
    if tier == "free" and counts_call and not check_free_limit(key, FREE_DAILY_CALLS):
        return _deny(429, f"free tier limit reached ({FREE_DAILY_CALLS}/day): upgrade at https://xbridgemcp.com")
    return AuthResult(ok=True, status=200, tier=tier)
