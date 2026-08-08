#!/usr/bin/env python3
"""
Build lecturer or student single-file .exe with edition branding.

  python bin/tools/build_edition_exe.py student
  python bin/tools/build_edition_exe.py lecturer

Student: Malaysia.utm embedded, student logo/icon, public UI
Lecturer: loads Malaysia.xml beside exe, lecturer logo/icon, Distribute tab;
           bundles student_template.exe for classroom zip export
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8")

_TOOLS = os.path.dirname(os.path.abspath(__file__))
BIN = os.path.dirname(_TOOLS)
ROOT = os.path.dirname(BIN)
DIST = os.path.join(ROOT, "dist")
EXE_OUT = os.path.join(ROOT, "exe")
BRAND = os.path.join(BIN, "branding")
if BIN not in sys.path:
    sys.path.insert(0, BIN)
from app_paths import GEOID_GFF_NAME, GEOID_GFF_LEGACY, GEOID_GSF_NAME
from geoid_vault import GEOID_GFF_SEALED, GEOID_GSF_SEALED
from param_vault import MALAYSIA_SEALED_UTM


def _pip(*packages):
    subprocess.check_call(
        [sys.executable, "-m", "pip", "install", "--upgrade", *packages],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def _run_seal():
    xml = os.path.join(ROOT, "Malaysia.xml")
    utm = os.path.join(ROOT, MALAYSIA_SEALED_UTM)
    if not os.path.isfile(xml):
        if os.path.isfile(utm):
            return utm
        raise SystemExit(f"ERROR: Need Malaysia.xml or {MALAYSIA_SEALED_UTM} in project root.")
    if not os.path.isfile(utm) or os.path.getmtime(xml) > os.path.getmtime(utm):
        print(f"  Sealing Malaysia.xml → {MALAYSIA_SEALED_UTM} …")
        subprocess.check_call(
            [sys.executable, os.path.join(BIN, "seal_malaysia.py"), "--utm"],
            cwd=ROOT,
        )
    return utm


def _ensure_branding(ed: str):
    logo = os.path.join(BRAND, ed, "logo.png")
    if not os.path.isfile(logo):
        print("  Generating branding placeholders …")
        subprocess.check_call([sys.executable, os.path.join(_TOOLS, "generate_branding.py")])


def _seal_geoid_for_student(work_dir: str) -> dict[str, str]:
    """Encrypt bin geoid files → geoid.utm / geoid_legacy.utm for student embed."""
    from geoid_vault import GEOID_GFF_SEALED, GEOID_GSF_SEALED, seal_geoid_file

    os.makedirs(work_dir, exist_ok=True)
    sealed: dict[str, str] = {}
    gsf = os.path.join(BIN, GEOID_GSF_NAME)
    if os.path.isfile(gsf):
        out = os.path.join(work_dir, GEOID_GSF_SEALED)
        seal_geoid_file(gsf, out)
        sealed["gsf"] = out
        print(f"  Sealed {GEOID_GSF_NAME} → {GEOID_GSF_SEALED}")
    gff_src = None
    for name in (GEOID_GFF_NAME, GEOID_GFF_LEGACY):
        candidate = os.path.join(BIN, name)
        if os.path.isfile(candidate):
            gff_src = candidate
            break
    if gff_src:
        out = os.path.join(work_dir, GEOID_GFF_SEALED)
        seal_geoid_file(gff_src, out)
        sealed["gff"] = out
        print(f"  Sealed {os.path.basename(gff_src)} → {GEOID_GFF_SEALED}")
    return sealed


def _write_edition_txt(ed: str) -> str:
    path = os.path.join(DIST, "edition.txt")
    os.makedirs(DIST, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(ed)
    return path


def build(edition_name: str):
    edition_name = edition_name.lower()
    if edition_name not in ("student", "lecturer"):
        raise SystemExit("Edition must be 'student' or 'lecturer'")

    exe_name = f"UTM_Coordinate_Wizard_{edition_name.capitalize()}"
    exe_path = os.path.join(EXE_OUT, f"{exe_name}.exe")
    work = os.path.join(DIST, f"build_utm_{edition_name}_work")
    os.makedirs(EXE_OUT, exist_ok=True)

    print()
    print("=" * 60)
    print(f"  BUILD — {edition_name.upper()} EDITION")
    print("=" * 60)
    print()

    _pip("pyinstaller", "pillow")
    _ensure_branding(edition_name)

    brand_dir = os.path.join(BRAND, edition_name)
    if edition_name == "student":
        lecturer_brand = os.path.join(BRAND, "lecturer")
        if os.path.isdir(lecturer_brand):
            brand_dir = lecturer_brand
    icon = os.path.join(brand_dir, "icon.ico")
    logo = os.path.join(brand_dir, "logo.png")
    icon_win = os.path.join(brand_dir, "icon_win.png")
    edition_txt = _write_edition_txt(edition_name)

    datas: list[tuple[str, str]] = [
        (edition_txt, "."),
        (logo, "."),
        (icon, "."),
    ]
    if os.path.isfile(icon_win):
        datas.append((icon_win, "."))

    if edition_name == "student":
        eap = _run_seal()
        datas.append((eap, "."))
        seal_dir = os.path.join(work, "_geoid_sealed")
        sealed = _seal_geoid_for_student(seal_dir)
        if sealed.get("gsf"):
            datas.append((sealed["gsf"], GEOID_GSF_SEALED))
        elif os.path.isfile(os.path.join(BIN, GEOID_GSF_NAME)):
            raise SystemExit(f"ERROR: failed to seal {GEOID_GSF_NAME}")
        else:
            print(f"  NOTE: bin/{GEOID_GSF_NAME} not found — geoid not embedded")
        if sealed.get("gff"):
            datas.append((sealed["gff"], GEOID_GFF_SEALED))
    else:
        # Build student exe first to embed as template for lecturer zip export
        student_exe = os.path.join(EXE_OUT, "UTM_Coordinate_Wizard_Student.exe")
        if not os.path.isfile(student_exe):
            print("  Building student template (required for lecturer) …")
            build("student")
        import shutil
        embed_dir = os.path.join(work, "_embed")
        os.makedirs(embed_dir, exist_ok=True)
        template_embed = os.path.join(embed_dir, "student_template.exe")
        shutil.copy2(student_exe, template_embed)
        datas.append((template_embed, "."))
        utm_full = os.path.join(BRAND, "assets", "utm_full.png")
        if os.path.isfile(utm_full):
            datas.append((utm_full, "utm_full.png"))

    if edition_name != "student":
        gsf = os.path.join(BIN, GEOID_GSF_NAME)
        if os.path.isfile(gsf):
            datas.append((gsf, GEOID_GSF_NAME))
        else:
            print(f"  NOTE: bin/{GEOID_GSF_NAME} not found — geoid grid not embedded (add before build)")

        gff = None
        for name in (GEOID_GFF_NAME, GEOID_GFF_LEGACY):
            candidate = os.path.join(BIN, name)
            if os.path.isfile(candidate):
                gff = candidate
                break
        if gff:
            datas.append((gff, GEOID_GFF_NAME))

    entry = os.path.join(BIN, "utm_coordinate_wizard.py")
    rth = os.path.join(BIN, "pyi_rth_00_win_boot.py")
    args = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm", "--clean",
        "--onefile", "--windowed",
        f"--name={exe_name}",
        f"--distpath={EXE_OUT}",
        f"--workpath={work}",
        f"--specpath={work}",
        "--paths", BIN,
        f"--runtime-hook={rth}",
        "--hidden-import=malaysia_zones",
        "--hidden-import=param_vault",
        "--hidden-import=geoid_vault",
        "--hidden-import=app_paths",
        "--hidden-import=ui_theme",
        "--hidden-import=win_boot",
        "--hidden-import=student_pack",
        "--hidden-import=PIL",
        "--hidden-import=PIL.Image",
        "--hidden-import=PIL.ImageTk",
        "--collect-submodules=PIL",
    ]
    if os.path.isfile(icon):
        args.extend(["--icon", icon])

    for src, dest in datas:
        args.extend(["--add-data", f"{src}{os.pathsep}{dest}"])

    args.append(entry)

    print(f"  Running PyInstaller → {exe_name}.exe …")
    subprocess.check_call(args, cwd=ROOT)

    if not os.path.isfile(exe_path):
        raise SystemExit(f"Build failed — {exe_path} not created")

    size_mb = os.path.getsize(exe_path) / (1024 * 1024)
    print()
    print("  DONE")
    print(f"  Exe  : {exe_path}")
    print(f"  Size : {size_mb:.1f} MB")
    if edition_name == "lecturer":
        xml_src = os.path.join(ROOT, "Malaysia.xml")
        xml_dst = os.path.join(EXE_OUT, "Malaysia.xml")
        if os.path.isfile(xml_src):
            import shutil
            shutil.copy2(xml_src, xml_dst)
            print(f"  Copied Malaysia.xml → {xml_dst}")
        print("  Malaysia.xml is beside the lecturer exe in exe\\")
        print("  Use the 'Distribute' tab to export student zip.")
    else:
        print(f"  {MALAYSIA_SEALED_UTM} + sealed geoid (.utm) embedded — no plain grid files.")
    print()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("edition", choices=["student", "lecturer"])
    args = ap.parse_args()
    build(args.edition)
