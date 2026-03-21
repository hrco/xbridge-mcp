import os
import sys
import json
import pytest
from unittest.mock import patch, MagicMock

# ---------------------------------------------------------------------------
# Stub out AWS deps so aws/src/shared/db.py is importable with no credentials.
# Must happen before any import of db or handler modules.
# ---------------------------------------------------------------------------
os.environ.setdefault('TABLE_NAME', 'test-table')

_mock_table = MagicMock()
_mock_dynamodb = MagicMock()
_mock_dynamodb.Table.return_value = _mock_table

_boto3_stub = MagicMock()
_boto3_stub.resource.return_value = _mock_dynamodb

_conditions_stub = MagicMock()
_botocore_stub = MagicMock()
_botocore_exceptions_stub = MagicMock()

sys.modules['boto3'] = _boto3_stub
sys.modules['boto3.dynamodb'] = MagicMock()
sys.modules['boto3.dynamodb.conditions'] = _conditions_stub
sys.modules['botocore'] = _botocore_stub
sys.modules['botocore.exceptions'] = _botocore_exceptions_stub

# Add aws/src/ to path so `shared.db` resolves (same as Lambda runtime)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'aws', 'src'))

# Now safe to import — db.py will use the stubbed boto3
import shared.db as _db_module  # noqa: E402  (ensure module is cached)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_item(tier='free', calls_today=0, call_date='2026-03-19'):
    return {'key': 'test-uuid', 'tier': tier, 'email': 'a@b.com',
            'calls_today': calls_today, 'call_date': call_date}


def _invoke(key='test-uuid'):
    event = {'body': json.dumps({'key': key})}
    from aws.src.validate_key.handler import lambda_handler
    return lambda_handler(event, None)


# ---------------------------------------------------------------------------
# Tests — patch at aws.src.shared.db (where the names live at call time)
# ---------------------------------------------------------------------------

@patch('aws.src.validate_key.handler.get_key')
def test_unknown_key_returns_invalid(mock_get):
    mock_get.return_value = None
    resp = _invoke('unknown')
    assert json.loads(resp['body']) == {'valid': False}


@patch('aws.src.validate_key.handler.get_key')
def test_paid_key_returns_unlimited(mock_get):
    mock_get.return_value = _make_item(tier='paid')
    resp = _invoke()
    body = json.loads(resp['body'])
    assert body['valid'] is True
    assert body['tier'] == 'paid'
    assert body['calls_remaining'] is None


@patch('aws.src.validate_key.handler.try_increment_free')
@patch('aws.src.validate_key.handler.get_key')
def test_free_key_under_limit(mock_get, mock_inc):
    mock_get.return_value = _make_item(tier='free', calls_today=10)
    mock_inc.return_value = {'valid': True, 'tier': 'free', 'calls_remaining': 39}
    resp = _invoke()
    body = json.loads(resp['body'])
    assert body['calls_remaining'] == 39


@patch('aws.src.validate_key.handler.try_increment_free')
@patch('aws.src.validate_key.handler.get_key')
def test_free_key_at_limit(mock_get, mock_inc):
    mock_get.return_value = _make_item(tier='free', calls_today=50)
    mock_inc.return_value = {'valid': True, 'tier': 'free', 'calls_remaining': 0}
    resp = _invoke()
    body = json.loads(resp['body'])
    assert body['calls_remaining'] == 0
