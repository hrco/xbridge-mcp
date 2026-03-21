import json
import os
import uuid
import httpx

_CA = '6vUhppYep18WSncUDR6Brt9yZw31ycLDPDEHo13pump'
_RPC = 'https://api.mainnet-beta.solana.com'
_LS_API_KEY = os.environ.get('LS_API_KEY', '')
_LS_STORE_ID = os.environ.get('LS_STORE_ID', '')
_MIN_TOKENS = 1000


def lambda_handler(event, context):
    body = json.loads(event.get('body') or '{}')
    wallet = body.get('wallet', '').strip()

    if not wallet:
        return _resp(400, {'error': 'wallet required'})

    balance = _get_balance(wallet)
    if balance < _MIN_TOKENS:
        return _resp(200, {'eligible': False, 'balance': balance})

    coupon = _create_ls_coupon()
    return _resp(200, {'eligible': True, 'coupon': coupon, 'balance': balance})


def _get_balance(wallet: str) -> float:
    payload = {
        'jsonrpc': '2.0', 'id': 1,
        'method': 'getTokenAccountsByOwner',
        'params': [wallet, {'mint': _CA}, {'encoding': 'jsonParsed'}],
    }
    try:
        resp = httpx.post(_RPC, json=payload, timeout=5.0)
        accounts = resp.json().get('result', {}).get('value', [])
        if not accounts:
            return 0.0
        return float(accounts[0]['account']['data']['parsed']['info']['tokenAmount']['uiAmount'] or 0)
    except Exception:
        return 0.0


def _create_ls_coupon() -> str:
    code = f'XBRDG-{str(uuid.uuid4())[:8].upper()}'
    httpx.post(
        'https://api.lemonsqueezy.com/v1/discounts',
        headers={'Authorization': f'Bearer {_LS_API_KEY}', 'Accept': 'application/vnd.api+json'},
        json={'data': {'type': 'discounts', 'attributes': {
            'name': '$XBRDG holder discount',
            'code': code,
            'amount': 20,
            'amount_type': 'percent',
            'duration': 'once',
            'max_redemptions': 1,
            'store_id': int(_LS_STORE_ID) if _LS_STORE_ID else 0,
        }}},
        timeout=5.0,
    )
    return code


def _resp(status: int, body: dict) -> dict:
    return {
        'statusCode': status,
        'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
        'body': json.dumps(body),
    }
