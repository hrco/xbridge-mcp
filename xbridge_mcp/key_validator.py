import os
import time
import httpx

_VALIDATE_URL = os.environ.get('VALIDATE_URL', 'https://y0xx9n1oz7.execute-api.eu-west-1.amazonaws.com/validate')
_CACHE_TTL = 60.0

_cache: dict = {'valid': None, 'tier': None, 'calls_remaining': None, 'ts': 0.0}


async def validate(key: str | None) -> dict:
    if not key:
        return {'valid': True, 'tier': 'self-hosted'}

    now = time.monotonic()
    if _cache['valid'] is not None and (now - _cache['ts']) < _CACHE_TTL:
        return {k: v for k, v in _cache.items() if k != 'ts'}

    result = await _fetch_validation(key)
    _cache.update({**result, 'ts': now})
    return result


async def _fetch_validation(key: str) -> dict:
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.post(_VALIDATE_URL, json={'key': key})
            return resp.json()
    except Exception:
        if _cache['valid'] is not None:
            return dict(_cache)
        return {'valid': True, 'tier': 'self-hosted'}
