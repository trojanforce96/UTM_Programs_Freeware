#!/usr/bin/env python3
"""Build lecturer thank-you package (branded exe + Malaysia.xml + README)."""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import zipfile

sys.stdout.reconfigure(encoding="utf-8")

_TOOLS = os.path.dirname(os.path.abspath(__file__))
BIN = os.path.dirname(_TOOLS)
ROOT = os.path.dirname(BIN)
DIST = os.path.join(ROOT, "dist")
EXE_OUT = os.path.join(ROOT, "exe")
OUT = os.path.join(DIST, "UTM_Coordinate_Wizard_Lecturer")
ZIP_PATH = os.path.join(DIST, "UTM_Coordinate_Wizard_Lecturer.zip")
EXE = os.path.join(EXE_OUT, "UTM_Coordinate_Wizard_Lecturer.exe")

if BIN not in sys.path:
    sys.path.insert(0, BIN)


def _ensure_lecturer_exe():
    if os.path.isfile(EXE):
        print(f"  Using {EXE}")
        return
    print("  Building lecturer exe (includes student template) …")
    subprocess.check_call(
        [sys.executable, os.path.join(_TOOLS, "build_edition_exe.py"), "lecturer"], cwd=ROOT)


def _write_readme(out: str):
    with open(os.path.join(out, "README_FOR_LECTURER.txt"), "w", encoding="utf-8", newline="\r\n") as f:
        f.write("""UTM COORDINATE WIZARD — LECTURER EDITION
======================================

Thank you for your guidance on how Malaysian coordinate conversion works —
this lecturer edition is built with you and your students in mind.
From UTM Student, For UTM Student.

CONTENTS
  UTM_Coordinate_Wizard_Lecturer.exe   Your copy (UTM logo/icon)
  Malaysia.xml                         Support file — keep in the same folder as the .exe
  README_FOR_LECTURER.txt              This file

  Geoid grid and student template are embedded in the lecturer .exe
  (no separate WGEOID files needed beside this folder).

RUN
  Double-click UTM_Coordinate_Wizard_Lecturer.exe (no Python needed).
  Keep Malaysia.xml in the same folder as the .exe.

TABS
  Convert     — single-point conversion; Export KML/KMZ after Convert
  Batch       — many points: paste from Excel, Import TXT/CSV/Excel,
                Convert All, export Excel / CSV / KML/KMZ
  Geoid       — WGeoid04 undulation lookup
  Distribute  — package the student edition for your class
  Help        — step-by-step guide for every tab

BATCH TIPS
  • Paste coordinate columns only — values go to Northing/Easting (or Lat/Lon),
    not the Name column. Include a name column only if your sheet has point names.
  • Lat/Lon rows auto-detect which value is latitude (|value| ≤ 90°).
  • For grid coordinates, choose  Paste column order  (N then E or E then N)
    above the table, or use a header row (Northing, Easting, …).
  • When  From  is UTM, set Zone and Hemisphere above the table (defaults for
    all rows); you can still override per row in the table.
  • Row numbers (#) are automatic; Name is optional.

DISTRIBUTE TO STUDENTS
  1. Open the app → tab  Distribute
  2. Optionally type your name — it appears as
     "From your lecturer <your name>" in the student README
  3. Click  Export Student ZIP…  and save
  4. Share the zip — students double-click the .exe inside; no extra files
     (student zip = .exe + README only; geoid is inside the student .exe)

  Optional:  Generate class test coordinates…  for practice sets.

CUSTOM LOGO / ICON (developer rebuild only)
  Replace files in bin/branding/lecturer/ and bin/branding/student/
  then run 9_EA_Build_Lecturer_Package.bat again.

With gratitude,
Firdaus Shah / Ezam & Associates
""")


def build():
    print()
    print("=" * 60)
    print("  LECTURER PACKAGE (branded exe + Malaysia.xml)")
    print("=" * 60)
    print()

    logo = os.path.join(BIN, "branding", "lecturer", "logo.png")
    if not os.path.isfile(logo):
        subprocess.check_call([sys.executable, os.path.join(_TOOLS, "generate_branding.py")])
    else:
        print("  Using existing branding assets")

    if BIN not in sys.path:
        sys.path.insert(0, BIN)
    from app_paths import malaysia_params_dir
    xml = os.path.join(malaysia_params_dir(), "Malaysia.xml")
    if not os.path.isfile(xml):
        raise SystemExit(f"ERROR: Malaysia.xml required in {malaysia_params_dir()}.")

    _ensure_lecturer_exe()

    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    os.makedirs(OUT)

    shutil.copy2(EXE, os.path.join(OUT, os.path.basename(EXE)))
    shutil.copy2(xml, os.path.join(OUT, "Malaysia.xml"))
    _write_readme(OUT)
    print("  + lecturer exe (custom logo/icon)")
    print("  + Malaysia.xml")

    if os.path.isfile(ZIP_PATH):
        os.remove(ZIP_PATH)
    with zipfile.ZipFile(ZIP_PATH, "w", zipfile.ZIP_DEFLATED) as zf:
        for name in os.listdir(OUT):
            zf.write(os.path.join(OUT, name), name)

    print()
    print(f"  Folder : {OUT}")
    print(f"  Zip    : {ZIP_PATH}")
    print()


if __name__ == "__main__":
    build()
