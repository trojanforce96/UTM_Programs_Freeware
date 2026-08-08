"""Encrypt / decrypt Malaysia parameter XML (EAP1 vault)."""
import hashlib
import os
import sys
import zlib

MALAYSIA_SEALED_EA = "Malaysia.eap"
MALAYSIA_SEALED_UTM = "Malaysia.utm"

_MAGIC = b"EAP1"
_PBKDF2_ITERS = 120_000


def malaysia_sealed_names():
    """Edition-prioritized sealed param filenames to try at runtime."""
    if getattr(sys, "frozen", False):
        flag = os.path.join(sys._MEIPASS, "edition.txt")
        if os.path.isfile(flag):
            with open(flag, encoding="utf-8") as f:
                if f.read().strip().lower() == "student":
                    return (MALAYSIA_SEALED_UTM, MALAYSIA_SEALED_EA)
        return (MALAYSIA_SEALED_EA, MALAYSIA_SEALED_UTM)
    if os.environ.get("EA_EDITION", "dev").lower() == "student":
        return (MALAYSIA_SEALED_UTM, MALAYSIA_SEALED_EA)
    return (MALAYSIA_SEALED_EA, MALAYSIA_SEALED_UTM)


def _keystream(key: bytes, length: int) -> bytes:
    out = b""
    n = 0
    while len(out) < length:
        out += hashlib.sha256(key + n.to_bytes(4, "big")).digest()
        n += 1
    return out[:length]


def vault_key() -> bytes:
    """Application key — same key used by seal_malaysia.py."""
    env = os.environ.get("EA_VAULT_KEY")
    if env:
        return env.encode("utf-8")
    a = bytes([0x45, 0x7A, 0x61, 0x6D, 0x26, 0x41, 0x73, 0x73, 0x6F, 0x63])
    b = bytes([0x2E, 0x4D, 0x59, 0x2E, 0x56, 0x61, 0x75, 0x6C, 0x74, 0x2E])
    c = bytes([0x32, 0x30, 0x32, 0x36, 0x2E, 0x44, 0x6F, 0x4E, 0x6F, 0x54])
    d = bytes([0x53, 0x68, 0x61, 0x72, 0x65, 0x2E])
    return a + b + c + d


def encrypt_bytes(plaintext: bytes, key=None) -> bytes:
    key = key or vault_key()
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", key, salt, _PBKDF2_ITERS)
    payload = zlib.compress(plaintext, 9)
    stream = _keystream(dk, len(payload))
    cipher = bytes(x ^ y for x, y in zip(payload, stream))
    return _MAGIC + salt + cipher


def decrypt_bytes(blob: bytes, key=None) -> bytes:
    key = key or vault_key()
    if not blob.startswith(_MAGIC):
        raise ValueError("Not an EA parameter vault file (expected EAP1 header)")
    salt, cipher = blob[4:20], blob[20:]
    dk = hashlib.pbkdf2_hmac("sha256", key, salt, _PBKDF2_ITERS)
    stream = _keystream(dk, len(cipher))
    payload = bytes(x ^ y for x, y in zip(cipher, stream))
    return zlib.decompress(payload)
