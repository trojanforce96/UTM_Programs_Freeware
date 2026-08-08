"""Paths for dev, PyInstaller bundle, lecturer (external XML), and edition branding."""
import os
import sys

_EDITION_CACHE = None

GEOID_GSF_NAME = "WGeoid04.gsf"   # Topcon ASCII grid (preferred — matches JUPEM WGeoid04)
GEOID_GFF_NAME = "WGEOID04.gff"   # Topcon binary grid (legacy / MAGNET companion)
GEOID_GFF_LEGACY = "wgeoid04.gff"  # older copies / Windows case variants

from geoid_vault import GEOID_GFF_SEALED, GEOID_GSF_SEALED
from param_vault import MALAYSIA_SEALED_EA, MALAYSIA_SEALED_UTM, malaysia_sealed_names


def is_frozen():
    return getattr(sys, "frozen", False)


def exe_dir():
    """Directory containing the .exe (or project root when running as script)."""
    if is_frozen():
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def edition():
    """dev | lecturer | student"""
    global _EDITION_CACHE
    if _EDITION_CACHE:
        return _EDITION_CACHE
    if is_frozen():
        flag = os.path.join(sys._MEIPASS, "edition.txt")
        if os.path.isfile(flag):
            with open(flag, encoding="utf-8") as f:
                _EDITION_CACHE = f.read().strip().lower() or "student"
                return _EDITION_CACHE
    _EDITION_CACHE = os.environ.get("EA_EDITION", "dev").lower()
    return _EDITION_CACHE


def is_lecturer():
    return edition() == "lecturer" or os.environ.get("EA_LECTURER") == "1"


def is_student():
    return edition() == "student"


def is_ea_app():
    """EA Coordinate Wizard (dev script or 5_EA Coordinate Wizard.exe — not UTM editions)."""
    if is_frozen():
        return not os.path.isfile(os.path.join(sys._MEIPASS, "edition.txt"))
    return edition() == "dev"


MISC_DIR = "Misc"
PACKAGE_DIR = "package"


def project_root():
    """Malaysia.eap / Malaysia.utm / Malaysia.xml — lecturer uses XML beside exe."""
    if is_frozen():
        if is_lecturer():
            xml = os.path.join(exe_dir(), "Malaysia.xml")
            if os.path.isfile(xml):
                return exe_dir()
        for name in malaysia_sealed_names():
            bundled = os.path.join(sys._MEIPASS, name)
            if os.path.isfile(bundled):
                return sys._MEIPASS
        for name in malaysia_sealed_names():
            sidecar = os.path.join(exe_dir(), name)
            if os.path.isfile(sidecar):
                return exe_dir()
        return sys._MEIPASS
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def misc_dir():
    return os.path.join(project_root(), MISC_DIR)


def malaysia_params_dir():
    """Malaysia.xml / .eap / .utm — dev builds use Misc/; lecturer exe uses XML beside exe."""
    if is_frozen():
        return project_root()
    misc = misc_dir()
    if os.path.isdir(misc):
        return misc
    return project_root()


def package_dir():
    return os.path.join(project_root(), PACKAGE_DIR)


def bin_dir():
    if is_frozen():
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))


def resource(name):
    if name in (*malaysia_sealed_names(), "Malaysia.xml"):
        return os.path.join(malaysia_params_dir(), name)
    if name in (GEOID_GSF_NAME, GEOID_GFF_NAME, GEOID_GFF_LEGACY):
        return geoid_file_path()
    base = bin_dir()
    if is_frozen():
        return os.path.join(base, name)
    if is_ea_app():
        ea_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), name)
        if os.path.isfile(ea_path):
            return ea_path
    ed = edition() if edition() in ("lecturer", "student") else None
    if ed:
        branded = os.path.join(base, "branding", ed, name)
        if os.path.isfile(branded):
            return branded
    fallback = os.path.join(base, name)
    return fallback


def _geoid_search_dirs():
    dirs = []
    if is_frozen():
        dirs.append(sys._MEIPASS)
    dirs.append(bin_dir())
    dirs.append(exe_dir())
    root = project_root()
    if root:
        dirs.append(root)
    return dirs


def _find_geoid_file(names, *, required=False, default_name=None):
    seen = set()
    for d in _geoid_search_dirs():
        if not d:
            continue
        for name in names:
            p = os.path.join(d, name)
            key = os.path.normcase(p)
            if key in seen:
                continue
            seen.add(key)
            if os.path.isfile(p):
                return p
        if os.path.isdir(d):
            for entry in os.listdir(d):
                for name in names:
                    if entry.lower() == name.lower():
                        p = os.path.join(d, entry)
                        key = os.path.normcase(p)
                        if key in seen:
                            continue
                        seen.add(key)
                        if os.path.isfile(p):
                            return p
    if required:
        raise FileNotFoundError(
            f"Geoid grid not found ({names[0]}).\n"
            f"Place {GEOID_GSF_NAME} in bin\\ (dev) or beside the .exe.")
    return os.path.join(bin_dir(), default_name or names[0])


def geoid_gsf_path(*, required=False):
    """Resolve WGeoid04.gsf — student exe uses sealed geoid.utm."""
    names = (GEOID_GSF_SEALED, GEOID_GSF_NAME) if is_student() else (GEOID_GSF_NAME, GEOID_GSF_SEALED)
    return _find_geoid_file(
        names,
        required=required,
        default_name=GEOID_GSF_SEALED if is_student() else GEOID_GSF_NAME,
    )


def geoid_gff_path(*, required=False):
    """Resolve WGEOID04.gff — student exe uses sealed geoid_legacy.utm."""
    if is_student():
        return _find_geoid_file(
            (GEOID_GFF_SEALED, GEOID_GFF_NAME, GEOID_GFF_LEGACY),
            required=required,
            default_name=GEOID_GFF_SEALED,
        )
    return _find_geoid_file(
        (GEOID_GFF_NAME, GEOID_GFF_LEGACY, GEOID_GFF_SEALED),
        required=required,
        default_name=GEOID_GFF_NAME,
    )


def geoid_file_path(*, required=False):
    """Prefer WGeoid04.gsf; fall back to WGEOID04.gff."""
    gsf = geoid_gsf_path()
    if os.path.isfile(gsf):
        return gsf
    return geoid_gff_path(required=required)


def bundled_path(name):
    """File embedded in PyInstaller bundle (_MEIPASS), e.g. student_template.exe."""
    if is_frozen():
        return os.path.join(sys._MEIPASS, name)
    return os.path.join(package_dir(), name)
