import pytest
import time
from unittest.mock import AsyncMock, patch


@pytest.fixture(autouse=True)
def reset_cache():
    from xbridge_mcp import key_validator
    key_validator._cache.update({'valid': None, 'tier': None, 'calls_remaining': None, 'ts': 0.0})
    yield


@pytest.mark.asyncio
async def test_no_key_returns_self_hosted():
    from xbridge_mcp.key_validator import validate
    result = await validate(key=None)
    assert result == {'valid': True, 'tier': 'self-hosted'}


@pytest.mark.asyncio
@patch('xbridge_mcp.key_validator._fetch_validation')
async def test_paid_key_passes(mock_fetch):
    mock_fetch.return_value = {'valid': True, 'tier': 'paid', 'calls_remaining': None}
    from xbridge_mcp.key_validator import validate
    result = await validate(key='paid-uuid')
    assert result['valid'] is True
    assert result['tier'] == 'paid'


@pytest.mark.asyncio
@patch('xbridge_mcp.key_validator._fetch_validation')
async def test_result_is_cached(mock_fetch):
    mock_fetch.return_value = {'valid': True, 'tier': 'paid', 'calls_remaining': None}
    from xbridge_mcp.key_validator import validate
    await validate(key='uuid')
    await validate(key='uuid')
    assert mock_fetch.call_count == 1  # only one real call


@pytest.mark.asyncio
@patch('xbridge_mcp.key_validator._fetch_validation')
async def test_rate_limited_free_key(mock_fetch):
    mock_fetch.return_value = {'valid': True, 'tier': 'free', 'calls_remaining': 0}
    from xbridge_mcp.key_validator import validate
    result = await validate(key='free-uuid')
    assert result['calls_remaining'] == 0
