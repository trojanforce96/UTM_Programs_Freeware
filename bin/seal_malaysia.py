#!/usr/bin/env python3
"""Developer tool — seal plain Malaysia.xml into encrypted Malaysia.eap / Malaysia.utm."""
import argparse
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
_BIN = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_BIN)
if _BIN not in sys.path:
    sys.path.insert(0, _BIN)

from app_paths import malaysia_params_dir
from param_vault import (
    MALAYSIA_SEALED_EA,
    MALAYSIA_SEALED_UTM,
    decrypt_bytes,
    encrypt_bytes,
)


def _is_sealed_path(path: str) -> bool:
    low = path.lower()
    return low.endswith(".utm") or low.endswith(".eap")


def main():
    ap = argparse.ArgumentParser(description="Seal or unseal Malaysia projection parameters")
    ap.add_argument("--unseal", action="store_true",
                    help="Decrypt sealed file → Malaysia.xml (developer recovery)")
    ap.add_argument("--utm", action="store_true",
                    help=f"Output {MALAYSIA_SEALED_UTM} (UTM student); default is {MALAYSIA_SEALED_EA}")
    ap.add_argument("--in", dest="in_path",
                    default=os.path.join(malaysia_params_dir(), "Malaysia.xml"))
    ap.add_argument("--out", dest="out_path", default=None)
    args = ap.parse_args()

    default_out = MALAYSIA_SEALED_UTM if args.utm else MALAYSIA_SEALED_EA
    out_path = args.out_path or os.path.join(malaysia_params_dir(), default_out)

    if args.unseal:
        sealed = out_path if _is_sealed_path(out_path) and os.path.isfile(out_path) else args.in_path
        if not _is_sealed_path(sealed):
            sealed = args.in_path
        out_xml = args.in_path if _is_sealed_path(args.in_path) else os.path.join(malaysia_params_dir(), "Malaysia.xml")
        if _is_sealed_path(out_xml):
            out_xml = os.path.join(malaysia_params_dir(), "Malaysia.xml")
        with open(sealed, "rb") as f:
            plain = decrypt_bytes(f.read())
        with open(out_xml, "wb") as f:
            f.write(plain)
        print(f"Unsealed → {out_xml}  ({len(plain):,} bytes)")
        return

    if not os.path.isfile(args.in_path):
        print(f"Missing: {args.in_path}", file=sys.stderr)
        sys.exit(1)
    with open(args.in_path, "rb") as f:
        plain = f.read()
    sealed = encrypt_bytes(plain)
    with open(out_path, "wb") as f:
        f.write(sealed)
    print(f"Sealed {args.in_path}")
    print(f"  → {out_path}  ({len(sealed):,} bytes)")
    print(f"  Distribute {os.path.basename(out_path)} only — keep Malaysia.xml on your machine.")


if __name__ == "__main__":
    main()
