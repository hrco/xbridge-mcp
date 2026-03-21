import json
import re
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from shared.db import create_key, email_exists
from shared.email import send_key_email

_EMAIL_RE = re.compile(r'^[^@]+@[^@]+\.[^@]+$')


def lambda_handler(event, context):
    body = json.loads(event.get('body') or '{}')
    email = body.get('email', '').strip().lower()

    if not _EMAIL_RE.match(email):
        return _resp(400, {'error': 'Invalid email'})

    if email_exists(email):
        return _resp(409, {'error': 'Email already registered. Check your inbox.'})

    key = create_key(email=email, tier='free')
    send_key_email(email, key, 'free')
    return _resp(200, {'success': True})


def _resp(status: int, body: dict) -> dict:
    return {
        'statusCode': status,
        'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
        'body': json.dumps(body),
    }
