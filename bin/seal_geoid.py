#!/usr/bin/env python3
"""Developer tool — seal plain geoid grids into encrypted .utm for student builds."""
import argparse
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
_BIN = os.path.dirname(os.path.abspath(__file__))
if _BIN not in sys.path:
    sys.path.insert(0, _BIN)

from app_paths import GEOID_GFF_LEGACY, GEOID_GFF_NAME, GEOID_GSF_NAME
from geoid_vault import GEOID_GFF_SEALED, GEOID_GSF_SEALED, read_geoid_bytes, seal_geoid_file
from param_vault import decrypt_bytes


def main():
    ap = argparse.ArgumentParser(description="Seal geoid grids for student edition")
    ap.add_argument("--unseal", action="store_true", help="Decrypt .utm → original filename")
    ap.add_argument("--out-dir", default=_BIN, help="Output directory for sealed files")
    args = ap.parse_args()

    if args.unseal:
        for sealed, plain_name in ((GEOID_GSF_SEALED, GEOID_GSF_NAME), (GEOID_GFF_SEALED, GEOID_GFF_NAME)):
            src = os.path.join(args.out_dir, sealed)
            if not os.path.isfile(src):
                continue
            dst = os.path.join(args.out_dir, plain_name)
            with open(dst, "wb") as f:
                f.write(read_geoid_bytes(src))
            print(f"Unsealed {sealed} → {plain_name} ({os.path.getsize(dst):,} bytes)")
        return

    os.makedirs(args.out_dir, exist_ok=True)
    gsf = os.path.join(_BIN, GEOID_GSF_NAME)
    if os.path.isfile(gsf):
        out = os.path.join(args.out_dir, GEOID_GSF_SEALED)
        seal_geoid_file(gsf, out)
        print(f"Sealed {GEOID_GSF_NAME} → {out} ({os.path.getsize(out):,} bytes)")
    gff = None
    for name in (GEOID_GFF_NAME, GEOID_GFF_LEGACY):
        p = os.path.join(_BIN, name)
        if os.path.isfile(p):
            gff = p
            break
    if gff:
        out = os.path.join(args.out_dir, GEOID_GFF_SEALED)
        seal_geoid_file(gff, out)
        print(f"Sealed {os.path.basename(gff)} → {out} ({os.path.getsize(out):,} bytes)")
    print("Student build embeds .utm only — keep plain .gsf/.gff in bin\\ for developers.")


if __name__ == "__main__":
    main()
