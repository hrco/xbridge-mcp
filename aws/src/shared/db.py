import os
import uuid
import boto3
from datetime import datetime, timezone, timedelta
from boto3.dynamodb.conditions import Attr, Key
from botocore.exceptions import ClientError

_dynamodb = boto3.resource('dynamodb')
_table = _dynamodb.Table(os.environ['TABLE_NAME'])


def get_key(key: str) -> dict | None:
    resp = _table.get_item(Key={'key': key})
    return resp.get('Item')


def create_key(email: str, tier: str, subscription_id: str = '') -> str:
    new_key = str(uuid.uuid4())
    item = {
        'key': new_key,
        'email': email,
        'tier': tier,
        'calls_today': 0,
        'call_date': _today(),
        'created_at': datetime.now(timezone.utc).isoformat(),
    }
    if tier == 'paid':
        item['TTL'] = _ttl_days(30)
    if subscription_id:
        item['subscription_id'] = subscription_id
    _table.put_item(Item=item)
    return new_key


def extend_paid_key(subscription_id: str, days: int = 30):
    resp = _table.query(
        IndexName='subscription-index',
        KeyConditionExpression=Key('subscription_id').eq(subscription_id),
    )
    for item in resp.get('Items', []):
        _table.update_item(
            Key={'key': item['key']},
            UpdateExpression='SET #t = :ttl, tier = :paid',
            ExpressionAttributeNames={'#t': 'TTL'},
            ExpressionAttributeValues={':ttl': _ttl_days(days), ':paid': 'paid'},
        )


def downgrade_key(subscription_id: str):
    resp = _table.query(
        IndexName='subscription-index',
        KeyConditionExpression=Key('subscription_id').eq(subscription_id),
    )
    for item in resp.get('Items', []):
        _table.update_item(
            Key={'key': item['key']},
            UpdateExpression='REMOVE #t SET tier = :free',
            ExpressionAttributeNames={'#t': 'TTL'},
            ExpressionAttributeValues={':free': 'free'},
        )


def try_increment_free(key: str) -> dict:
    today = _today()
    item = get_key(key)
    if not item:
        return {'valid': False}

    if item.get('call_date') != today:
        _table.update_item(
            Key={'key': key},
            UpdateExpression='SET calls_today = :one, call_date = :today',
            ExpressionAttributeValues={':one': 1, ':today': today},
        )
        return {'valid': True, 'tier': 'free', 'calls_remaining': 49}

    if int(item.get('calls_today', 0)) >= 50:
        return {'valid': True, 'tier': 'free', 'calls_remaining': 0}

    try:
        resp = _table.update_item(
            Key={'key': key},
            UpdateExpression='SET calls_today = calls_today + :one',
            ConditionExpression=Attr('calls_today').lt(50) & Attr('call_date').eq(today),
            ExpressionAttributeValues={':one': 1},
            ReturnValues='ALL_NEW',
        )
        new_count = int(resp['Attributes']['calls_today'])
        return {'valid': True, 'tier': 'free', 'calls_remaining': 50 - new_count}
    except ClientError as e:
        if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
            return {'valid': True, 'tier': 'free', 'calls_remaining': 0}
        raise


def email_exists(email: str) -> bool:
    resp = _table.query(
        IndexName='email-index',
        KeyConditionExpression=Key('email').eq(email),
    )
    return len(resp.get('Items', [])) > 0


def _today() -> str:
    return datetime.now(timezone.utc).strftime('%Y-%m-%d')


def _ttl_days(days: int) -> int:
    return int((datetime.now(timezone.utc) + timedelta(days=days)).timestamp())
