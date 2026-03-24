import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from shared.db import get_key

FREE_DAILY_LIMIT = 50


def lambda_handler(event, context):
    body = json.loads(event.get('body') or '{}')
    key = body.get('key', '').strip()

    if not key:
        return _resp(400, {'error': 'key required'})

    item = get_key(key)
    if not item:
        return _resp(200, {'valid': False})

    tier = item.get('tier', 'free')
    today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    calls_today = int(item.get('calls_today', 0)) if item.get('call_date') == today else 0

    if tier == 'paid':
        return _resp(200, {
            'valid': True,
            'tier': 'paid',
            'calls_today': calls_today,
            'calls_remaining': None,  # unlimited
        })

    return _resp(200, {
        'valid': True,
        'tier': 'free',
        'calls_today': calls_today,
        'calls_remaining': max(0, FREE_DAILY_LIMIT - calls_today),
        'daily_limit': FREE_DAILY_LIMIT,
    })


def _resp(status: int, body: dict) -> dict:
    return {
        'statusCode': status,
        'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
        'body': json.dumps(body),
    }
