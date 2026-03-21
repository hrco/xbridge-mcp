import os
import boto3

_ses = boto3.client('ses', region_name='eu-west-1')
_FROM = os.environ.get('SES_FROM', 'hello@xbridgemcp.com')


def send_key_email(to: str, key: str, tier: str):
    if tier == 'paid':
        subject = 'Your xBridge MCP Pro key 🚀'
        body = f"""Welcome to xBridge MCP Pro!

Your unlimited API key:

  XBRIDGE_KEY={key}

Add it to your .env file, then restart Claude Code.

Setup guide: https://xbridgemcp.com/setup
Support: hello@xbridgemcp.com

Thank you for supporting the project.
"""
    else:
        subject = 'Your xBridge MCP free key'
        body = f"""Here's your xBridge MCP free key (50 calls/day):

  XBRIDGE_KEY={key}

Add it to your .env and restart Claude Code.

Upgrade to Pro for unlimited: https://xbridgemcp.com/pro
"""

    _ses.send_email(
        Source=_FROM,
        Destination={'ToAddresses': [to]},
        Message={
            'Subject': {'Data': subject},
            'Body': {'Text': {'Data': body}},
        },
    )
