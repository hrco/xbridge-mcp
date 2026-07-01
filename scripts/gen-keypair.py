#!/usr/bin/env python3
"""One-time: generate Ed25519 keypair for license signing."""
import os, sys, base64
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization

KEYFILE = os.path.expanduser("~/.xbridge/signing_key")

private_key = Ed25519PrivateKey.generate()
public_key = private_key.public_key()

pub_raw = public_key.public_bytes(
    encoding=serialization.Encoding.Raw,
    format=serialization.PublicFormat.Raw,
)
pub_b64 = base64.b64encode(pub_raw).decode()

priv_raw = private_key.private_bytes(
    encoding=serialization.Encoding.Raw,
    format=serialization.PrivateFormat.Raw,
    encryption_algorithm=serialization.NoEncryption(),
)

os.makedirs(os.path.dirname(KEYFILE), exist_ok=True)
with open(KEYFILE, "wb") as f:
    f.write(priv_raw)
os.chmod(KEYFILE, 0o600)

print("PUBLIC KEY (paste into xbridge_mcp/tokenizer.py ED25519_PUBLIC_KEY_B64):")
print(pub_b64)
print(f"\nPrivate key saved to: {KEYFILE}")
print("KEEP THIS SECRET AND BACKED UP. Without it you cannot generate new keys.")
