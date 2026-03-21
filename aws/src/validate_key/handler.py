import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from shared.db import get_key, try_increment_free


def lambda_handler(event, context):

    body = json.loads(event.get('body') or '{}')
    key = body.get('key', '').strip()

    if not key:
        return _resp(400, {'error': 'key required'})

    item = get_key(key)
    if not item:
        return _resp(200, {'valid': False})

    tier = item.get('tier')

    if tier == 'paid':
        return _resp(200, {'valid': True, 'tier': 'paid', 'calls_remaining': None})

    result = try_increment_free(key)
    return _resp(200, result)


def _resp(status: int, body: dict) -> dict:
    return {
        'statusCode': status,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps(body),
    }
