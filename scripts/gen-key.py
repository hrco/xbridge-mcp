#!/usr/bin/env python3
"""CLI: generate a signed license key for a customer."""
import os, sys, json, time, base64, argparse
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization

KEYFILE = os.path.expanduser("~/.xbridge/signing_key")

def load_private_key():
    if "XBRIDGE_SIGNING_KEY" in os.environ:
        raw = base64.b64decode(os.environ["XBRIDGE_SIGNING_KEY"])
        return Ed25519PrivateKey.from_private_bytes(raw)
    if os.path.exists(KEYFILE):
        with open(KEYFILE, "rb") as f:
            return Ed25519PrivateKey.from_private_bytes(f.read())
    sys.exit("No signing key. Set XBRIDGE_SIGNING_KEY env var or run gen-keypair.py first.")

def make_key(email, tier, days, private_key):
    payload = {"email": email, "tier": tier, "exp": int(time.time()) + days * 86400}
    payload_bytes = json.dumps(payload).encode()
    sig = private_key.sign(payload_bytes)
    p = base64.urlsafe_b64encode(payload_bytes).rstrip(b"=").decode()
    s = base64.urlsafe_b64encode(sig).rstrip(b"=").decode()
    return f"xbrdg_v1.{p}.{s}"

if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Generate xBridge license key")
    p.add_argument("--email", required=True)
    p.add_argument("--tier", default="pro", choices=["pro", "founder"])
    p.add_argument("--days", type=int, default=30)
    args = p.parse_args()
    pk = load_private_key()
    print(make_key(args.email, args.tier, args.days, pk))
