import json
import re
import os
import sys
import logging

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from shared.db import get_key_by_email
from shared.email import send_key_email

log = logging.getLogger()
log.setLevel(logging.INFO)

_EMAIL_RE = re.compile(r'^[^@]+@[^@]+\.[^@]+$')
_OK = {'success': True, 'message': 'If that email is registered, your key is on its way.'}


def lambda_handler(event, context):
    body = json.loads(event.get('body') or '{}')
    email = body.get('email', '').strip().lower()

    if not _EMAIL_RE.match(email):
        return _resp(400, {'error': 'Invalid email'})

    # Always return 200 — don't leak whether email exists
    item = get_key_by_email(email)
    if item:
        try:
            send_key_email(email, item['key'], item.get('tier', 'free'))
        except Exception as e:
            log.error('SES send failed for %s: %s', email, e)
            # Still return 200 — email delivery is async concern, not caller's problem

    return _resp(200, _OK)


def _resp(status: int, body: dict) -> dict:
    return {
        'statusCode': status,
        'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
        'body': json.dumps(body),
    }
