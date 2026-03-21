import json
import os
import sys
import pytest
from unittest.mock import patch, MagicMock

# ---------------------------------------------------------------------------
# Stub out AWS deps so aws/src/shared/db.py and aws/src/shared/email.py are
# importable with no credentials.  Must happen before any import of those modules.
# ---------------------------------------------------------------------------
os.environ.setdefault('TABLE_NAME', 'test-table')

_mock_table = MagicMock()
_mock_dynamodb = MagicMock()
_mock_dynamodb.Table.return_value = _mock_table

_mock_ses = MagicMock()

_boto3_stub = MagicMock()
_boto3_stub.resource.return_value = _mock_dynamodb
_boto3_stub.client.return_value = _mock_ses

_conditions_stub = MagicMock()
_botocore_stub = MagicMock()
_botocore_exceptions_stub = MagicMock()

sys.modules['boto3'] = _boto3_stub
sys.modules['boto3.dynamodb'] = MagicMock()
sys.modules['boto3.dynamodb.conditions'] = _conditions_stub
sys.modules['botocore'] = _botocore_stub
sys.modules['botocore.exceptions'] = _botocore_exceptions_stub

# Now safe to import — db.py and email.py will use the stubbed boto3
import aws.src.shared.db as _db_module       # noqa: E402
import aws.src.shared.email as _email_module  # noqa: E402


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _invoke(event_name, email='user@test.com', sub_id='sub_123'):
    body = {
        'meta': {'event_name': event_name},
        'data': {
            'id': sub_id,
            'attributes': {'user_email': email, 'status': 'active'},
        }
    }
    from aws.src.webhook_handler.handler import lambda_handler
    return lambda_handler({'body': json.dumps(body), 'headers': {}}, None)


# ---------------------------------------------------------------------------
# Tests — patch at the module where the names are looked up at call time
# ---------------------------------------------------------------------------

@patch('aws.src.webhook_handler.handler.send_key_email')
@patch('aws.src.webhook_handler.handler.create_key', return_value='new-uuid-key')
def test_subscription_created_generates_key(mock_create, mock_email):
    resp = _invoke('subscription_created', email='buyer@test.com', sub_id='sub_abc')
    mock_create.assert_called_once_with(email='buyer@test.com', tier='paid', subscription_id='sub_abc')
    mock_email.assert_called_once_with('buyer@test.com', 'new-uuid-key', 'paid')
    assert resp['statusCode'] == 200


@patch('aws.src.webhook_handler.handler.extend_paid_key')
def test_subscription_updated_active_extends_ttl(mock_extend):
    _invoke('subscription_updated', sub_id='sub_abc')
    mock_extend.assert_called_once_with('sub_abc', days=30)


@patch('aws.src.webhook_handler.handler.downgrade_key')
def test_subscription_cancelled_downgrades(mock_downgrade):
    _invoke('subscription_cancelled', sub_id='sub_abc')
    mock_downgrade.assert_called_once_with('sub_abc')
