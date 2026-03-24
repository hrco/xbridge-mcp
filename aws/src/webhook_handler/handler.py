import json
import hmac
import hashlib
import logging
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from shared.db import create_key, extend_paid_key, downgrade_key, get_key_by_sub_id
from shared.email import send_key_email

log = logging.getLogger()
log.setLevel(logging.INFO)

_SECRET = os.environ.get('LS_SIGNING_SECRET', '').encode()


def lambda_handler(event, context):
    if not _verify_signature(event):
        return {'statusCode': 401, 'body': 'Unauthorized'}

    body = json.loads(event.get('body') or '{}')
    meta = body.get('meta', {})
    data = body.get('data', {})
    event_name = meta.get('event_name', '')
    attrs = data.get('attributes', {})
    sub_id = str(data.get('id', ''))

    log.info('LS event: %s sub_id: %s', event_name, sub_id)

    if event_name == 'subscription_created':
        email = attrs.get('user_email', '')
        # Idempotent — LS retries on 5xx, so check before creating
        existing = get_key_by_sub_id(sub_id)
        key = existing['key'] if existing else create_key(email=email, tier='paid', subscription_id=sub_id)
        if existing:
            log.info('Duplicate subscription_created for sub_id %s — resending email only', sub_id)
        try:
            send_key_email(email, key, 'paid')
        except Exception as e:
            log.error('SES failed for %s: %s', email, e)
            # Key exists in DB — user can retrieve via /keys/resend

    elif event_name == 'subscription_updated':
        status = attrs.get('status', '')
        if status == 'active':
            extend_paid_key(sub_id, days=30)

    elif event_name in ('subscription_cancelled', 'subscription_expired'):
        downgrade_key(sub_id)

    return {'statusCode': 200, 'body': 'ok'}


def _verify_signature(event: dict) -> bool:
    if not _SECRET:
        return True  # dev mode
    headers = {k.lower(): v for k, v in (event.get('headers') or {}).items()}
    signature = headers.get('x-signature', '')
    body = event.get('body', '')
    expected = hmac.new(_SECRET, body.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)
