"""Create student distribution zip (used from lecturer edition)."""
import os
import zipfile

UTM_STUDENT_EXE_NAME = "UTM_Coordinate_Wizard_Student.exe"
UTM_LECTURER_EXE_NAME = "UTM_Coordinate_Wizard_Lecturer.exe"
# Legacy name from older builds (lecturer template fallback)
LEGACY_STUDENT_EXE_NAME = "EA_Coordinate_Wizard_Student.exe"


def build_student_readme(lecturer_name=""):
    """Student README; optional lecturer name → 'From your lecturer Name'."""
    name = (lecturer_name or "").strip()
    if name:
        intro = f"From your lecturer {name} for classroom / assignment use."
    else:
        intro = "Distributed by your lecturer for classroom / assignment use."
    return f"""UTM COORDINATE WIZARD — STUDENT EDITION
======================================
{intro}
From UTM Student, For UTM Student.

HOW TO RUN
  Double-click:  {UTM_STUDENT_EXE_NAME}
  (No other files or Python install needed.)

TABS
  Convert  — one point at a time; paste with Ctrl+V; Export KML/KMZ
  Batch    — many points from Excel; Convert All; export Excel / CSV / KML/KMZ
  Geoid    — geoid height lookup
  Help     — full how-to for each tab

QUICK START — BATCH
  1. Set  From  and  To  at the top (same choices as Convert).
  2. Copy coordinate columns from Excel, click the table, press  Ctrl+V .
  3. Paste coordinates only (no name column needed) — rows auto-number in #.
  4. For UTM input, enter Zone and Hemisphere above the table.
  5. Click  Convert All , then export if needed.

QUICK START — CONVERT
  Paste a lat/lon or northing/easting pair into Input with  Ctrl+V .
  Lat/lon auto-detects; grid coords: y→Northing, x→Easting.

REQUIREMENTS
  Windows 10/11

NOTE
  Do not share or modify the files in this package.
"""


# Backward-compatible alias (no lecturer name).
README_STUDENT = build_student_readme()


def create_student_zip(dest_zip, student_exe_path, lecturer_name=""):
    if not os.path.isfile(student_exe_path):
        raise FileNotFoundError(
            f"Student executable not found:\n  {student_exe_path}\n"
            "Rebuild the lecturer edition (includes student template).")
    folder = os.path.dirname(dest_zip) or "."
    os.makedirs(folder, exist_ok=True)
    if os.path.isfile(dest_zip):
        os.remove(dest_zip)
    with zipfile.ZipFile(dest_zip, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(student_exe_path, UTM_STUDENT_EXE_NAME)
        zf.writestr("README_FOR_STUDENTS.txt", build_student_readme(lecturer_name))
    return dest_zip


def _frozen_student_template_path():
    """Embedded student .exe inside lecturer onefile build."""
    from app_paths import bundled_path, is_frozen

    if not is_frozen():
        return None
    candidates = [
        bundled_path("student_template.exe"),
        os.path.join(bundled_path("student_template.exe"), UTM_STUDENT_EXE_NAME),
        bundled_path(UTM_STUDENT_EXE_NAME),
        bundled_path(LEGACY_STUDENT_EXE_NAME),
    ]
    for p in candidates:
        if p and os.path.isfile(p):
            return p
    return None


def _utm_src_mtime(root):
    p = os.path.join(root, "bin", "utm_coordinate_wizard.py")
    return os.path.getmtime(p) if os.path.isfile(p) else 0


def describe_student_template(root=None):
    """Human-readable note for the Distribute tab."""
    from app_paths import bundled_path, exe_dir, is_frozen

    if root is None:
        root = exe_dir()
    if is_frozen():
        p = _frozen_student_template_path()
        if not p:
            return "Student template: missing — use Export again after reinstalling lecturer build"
        age = os.path.getmtime(p)
        src = _utm_src_mtime(root)
        if src > age:
            return (f"Student template: embedded ({UTM_STUDENT_EXE_NAME}) — "
                    "reinstall lecturer build to refresh embedded copy")
        return f"Student template: embedded in this lecturer .exe ({UTM_STUDENT_EXE_NAME})"

    dist_exe = os.path.join(root, "dist", UTM_STUDENT_EXE_NAME)
    if os.path.isfile(dist_exe):
        src = _utm_src_mtime(root)
        if src > os.path.getmtime(dist_exe):
            return f"Student template: {dist_exe} (will rebuild on export — source changed)"
        return f"Student template: {dist_exe}"
    return "Student template: not built yet (will build on export)"


def resolve_student_exe_path(*, rebuild_if_stale=True, root=None):
    """Path to the student .exe packaged into the classroom zip."""
    import subprocess
    import sys
    from app_paths import bundled_path, exe_dir, is_frozen

    if root is None:
        root = exe_dir()

    if is_frozen():
        p = _frozen_student_template_path()
        if p:
            return p
        raise FileNotFoundError(
            "Student template missing inside lecturer build.\n"
            "Reinstall the lecturer .exe from your latest package.")

    dist = os.path.join(root, "dist")
    student_exe = os.path.join(dist, UTM_STUDENT_EXE_NAME)
    tools = os.path.join(root, "bin", "tools")
    utm_src = os.path.join(root, "bin", "utm_coordinate_wizard.py")

    stale = not os.path.isfile(student_exe)
    if not stale and rebuild_if_stale and os.path.isfile(utm_src):
        stale = os.path.getmtime(utm_src) > os.path.getmtime(student_exe)

    if stale and rebuild_if_stale:
        subprocess.check_call(
            [sys.executable, os.path.join(tools, "build_edition_exe.py"), "student"],
            cwd=root,
        )

    if os.path.isfile(student_exe):
        return student_exe

    legacy = os.path.join(dist, LEGACY_STUDENT_EXE_NAME)
    if os.path.isfile(legacy):
        return legacy

    raise FileNotFoundError(
        "Could not build student executable.\n"
        "Run: python bin\\tools\\build_edition_exe.py student")
