"""Seal / read encrypted geoid grids for student edition (EAP1 — same vault as Malaysia params)."""
from __future__ import annotations

import os

GEOID_GSF_SEALED = "geoid.utm"
GEOID_GFF_SEALED = "geoid_legacy.utm"
_VAULT_MAGIC = b"EAP1"


def seal_geoid_file(src_path: str, dest_path: str) -> None:
    from param_vault import encrypt_bytes

    with open(src_path, "rb") as f:
        plain = f.read()
    os.makedirs(os.path.dirname(os.path.abspath(dest_path)) or ".", exist_ok=True)
    with open(dest_path, "wb") as f:
        f.write(encrypt_bytes(plain))


def read_geoid_bytes(path: str) -> bytes:
    """Return plaintext bytes from .gsf, .gff, or sealed .utm vault files."""
    with open(path, "rb") as f:
        raw = f.read()
    if raw.startswith(_VAULT_MAGIC):
        from param_vault import decrypt_bytes

        return decrypt_bytes(raw)
    return raw
