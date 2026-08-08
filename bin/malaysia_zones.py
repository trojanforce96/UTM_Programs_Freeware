"""Load Malaysia projection zones and datum transforms from Malaysia.xml / sealed params."""
import os
import xml.etree.ElementTree as ET

# EPSG skew-grid angle — same for all Peninsular Malaysia RSO variants
_MRSO_GAMMA_C = 323 + 7 / 60 + 48.3685 / 3600

# Wizard display names (stable UI order) keyed by XML <Name>
_CASSINI_WIZARD = {
    "Malaysia_CS-JOHOR": "Johor  (MRT48)",
    "Malaysia_CS-KEDAH_PERLIS": "Kedah & Perlis  (MRT48)",
    "Malaysia_CS-KELANTAN": "Kelantan  (MRT48)",
    "Malaysia_CS-NEGERI_MELAKA": "Negeri Sembilan & Melaka  (MRT48)",
    "Malaysia_CS-BARAT_LAUT_PAHANG": "Pahang – Barat Laut  (MRT48)",
    "Malaysia_CS-TIMUR_LAUT_PAHANG": "Pahang – Timur Laut  (MRT48)",
    "Malaysia_CS-BARAT_DAYA_PAHANG": "Pahang – Barat Daya  (MRT48)",
    "Malaysia_CS-TENGGARA_PAHANG": "Pahang – Tenggara  (MRT48)",
    "Malaysia_CS-PINANG": "Pinang  (MRT48)",
    "Malaysia_CS-ZUN_PERAK_UTARA": "Perak Utara  (MRT48)",
    "Malaysia_CS-ZUN_PERAK_SELATAN": "Perak Selatan  (MRT48)",
    "Malaysia_CS-SELANGOR": "Selangor  (MRT48)",
    "Malaysia_CS-TERENGGA": "Terengganu  (MRT48)",
    "Malaysia_CS-SINGAPURA": "Singapura  (MRT48)",
    "Malaysia_CS2000-Johor": "Johor  (GDM2000)",
    "Malaysia_CS2000-NSembilan_Melaka": "N. Sembilan & Melaka  (GDM2000)",
    "Malaysia_CS2000-Pahang": "Pahang  (GDM2000)",
    "Malaysia_CS2000-Selangor": "Selangor  (GDM2000)",
    "Malaysia_CS2000-Terengganu": "Terengganu  (GDM2000)",
    "Malaysia_CS2000-PPinang_SPerai": "P. Pinang & S. Perai  (GDM2000)",
    "Malaysia_CS2000-Kedah_Perlis": "Kedah & Perlis  (GDM2000)",
    "Malaysia_CS2000-Perak": "Perak  (GDM2000)",
    "Malaysia_CS2000-Kelantan": "Kelantan  (GDM2000)",
    "Malaysia_CS2009-Johor": "Johor  (GDM2009)",
    "Malaysia_CS2009-NSembilan_Melaka": "N. Sembilan & Melaka  (GDM2009)",
    "Malaysia_CS2009-Pahang": "Pahang  (GDM2009)",
    "Malaysia_CS2009-Selangor": "Selangor  (GDM2009)",
    "Malaysia_CS2009-Terengganu": "Terengganu  (GDM2009)",
    "Malaysia_CS2009-PPinang_SPerai": "P. Pinang & S. Perai  (GDM2009)",
    "Malaysia_CS2009-Kedah_Perlis": "Kedah & Perlis  (GDM2009)",
    "Malaysia_CS2009-Perak": "Perak  (GDM2009)",
    "Malaysia_CS2009-Kelantan": "Kelantan  (GDM2009)",
}

_RSO_WIZARD = {
    "Malaysia_RSO": ("Malaysia RSO  (MRT48)", "MRT48"),
    "Malaysia_RSO2000": ("Malaysia RSO  (GDM2000)", "GDM2000"),
    "Malaysia_RSO2009": ("Malaysia RSO  (GDM2009)", "GDM2009"),
}

_ZONE_ORDER = list(_CASSINI_WIZARD.values())


def _float_elem(elem, tag, default=None):
    el = elem.find(tag)
    if el is None or el.text is None:
        if default is not None:
            return default
        raise ValueError(f"Missing <{tag}> in {elem.findtext('Name')}")
    return float(el.text.strip())


def _p_array(elem, n):
    return [_float_elem(elem, f"P{i}") for i in range(n)]


def _mrt48_geo_origin(proj_elem, xml_name):
    """Geographic origin for MRT48 C_S — from <GeoLat0>/<GeoLon0> on the projection."""
    lat_el, lon_el = proj_elem.find("GeoLat0"), proj_elem.find("GeoLon0")
    if lat_el is not None and lon_el is not None and lat_el.text and lon_el.text:
        return float(lat_el.text), float(lon_el.text)
    raise ValueError(
        f"MRT48 projection {xml_name!r} is missing <GeoLat0> and <GeoLon0> in Malaysia.xml")


def _parse_malaysia_xml(root):
    by_name = {p.findtext("Name"): p for p in root.findall("Projection")}

    zones = []
    for xml_name, wiz_name in _CASSINI_WIZARD.items():
        p = by_name.get(xml_name)
        if p is None:
            raise FileNotFoundError(f"Projection {xml_name!r} not found in Malaysia.xml")
        datum = p.findtext("Datum")
        ptype = p.findtext("Type")
        z = {"name": wiz_name, "datum": datum, "type": ptype, "xml_name": xml_name}
        if ptype == "C_S":
            z["P"] = _p_array(p, 16)
            z["lat0"], z["lon0"] = _mrt48_geo_origin(p, xml_name)
        elif ptype == "C_S2000":
            z["P"] = _p_array(p, 4)
        else:
            raise ValueError(f"Unexpected type {ptype!r} for {xml_name}")
        zones.append(z)

    zones.sort(key=lambda z: _ZONE_ORDER.index(z["name"]))
    return zones, by_name


def _make_rso_zone(name, datum, ell, lat_c_deg, lon_c_deg, axis_azimuth_packed,
                   gamma_c_deg, scale, fe, fn, _rso_constants):
    az_deg = 360.0 + _packed_dms_to_deg(axis_azimuth_packed)
    c = _rso_constants(ell, lat_c_deg, lon_c_deg, az_deg, gamma_c_deg, scale)
    return {"name": name, "datum": datum, "type": "RSO", "FE": fe, "FN": fn, "_c": c}


def _packed_dms_to_deg(val):
    sign = -1 if val < 0 else 1
    val = abs(val)
    s = val % 100
    val = int(val) // 100
    m = val % 100
    d = val // 100
    return sign * (d + m / 60 + s / 3600)


def _parse_rso_zones(by_name, mod_everest, grs80, _rso_constants):
    ell_map = {"MRT48": mod_everest, "GDM2000": grs80, "GDM2009": grs80}
    rso = []
    for xml_name, (wiz_name, datum) in _RSO_WIZARD.items():
        p = by_name.get(xml_name)
        if p is None:
            raise FileNotFoundError(f"RSO projection {xml_name!r} not found")
        lat_c = _packed_dms_to_deg(_float_elem(p, "P3"))
        lon_c = _packed_dms_to_deg(_float_elem(p, "P2"))
        rso.append(_make_rso_zone(
            wiz_name, datum, ell_map[datum], lat_c, lon_c,
            _float_elem(p, "P0"), _MRSO_GAMMA_C, _float_elem(p, "P1"),
            _float_elem(p, "P4"), _float_elem(p, "P5"), _rso_constants))
    return rso


def _parse_transforms(root):
    out = {}
    for t in root.findall("Transform"):
        key = (t.get("from"), t.get("to"))
        out[key] = dict(
            tx=float(t.get("tx")), ty=float(t.get("ty")), tz=float(t.get("tz")),
            rx=float(t.get("rx")), ry=float(t.get("ry")), rz=float(t.get("rz")),
            ppm=float(t.get("ppm")))
    return out


def _load_xml_bytes(project_root):
    """Load parameter XML: sealed .eap/.utm (production) or Malaysia.xml (dev / lecturer)."""
    from param_vault import decrypt_bytes, malaysia_sealed_names

    try:
        from app_paths import malaysia_params_dir, is_frozen
        params_root = malaysia_params_dir() if not is_frozen() else project_root
    except ImportError:
        misc = os.path.join(project_root, "Misc")
        params_root = misc if os.path.isdir(misc) else project_root

    names = malaysia_sealed_names()
    primary = names[0]
    xml_path = os.path.join(params_root, "Malaysia.xml")
    dev = os.environ.get("EA_DEV") == "1"
    try:
        from app_paths import is_lecturer
        lecturer = is_lecturer()
    except ImportError:
        lecturer = False

    if (dev or lecturer) and os.path.isfile(xml_path):
        with open(xml_path, "rb") as f:
            return f.read(), xml_path

    def _read_sealed(path):
        _bin = os.path.dirname(os.path.abspath(__file__))
        if _bin not in __import__("sys").path:
            __import__("sys").path.insert(0, _bin)
        with open(path, "rb") as f:
            return decrypt_bytes(f.read()), path

    for name in names:
        sealed_path = os.path.join(params_root, name)
        if os.path.isfile(sealed_path):
            return _read_sealed(sealed_path)

    if getattr(__import__("sys"), "frozen", False) and not dev and not lecturer:
        meipass = __import__("sys")._MEIPASS
        for name in names:
            bundle = os.path.join(meipass, name)
            if os.path.isfile(bundle):
                return _read_sealed(bundle)

    if os.path.isfile(xml_path):
        raise FileNotFoundError(
            f"Plain Malaysia.xml found but {primary} is missing.\n"
            "Run:  python bin\\seal_malaysia.py\n"
            "Or set EA_DEV=1 for local development with plain XML.")

    raise FileNotFoundError(
        f"No parameter file in {project_root}\n"
        f"Expected {primary} (contact EA) or Malaysia.xml with EA_DEV=1.")


def load_malaysia_config(project_root, mod_everest, grs80, rso_constants_fn):
    """Return (ZONES, RSO_ZONES, DATUM_TRANSFORMS) from sealed params or Malaysia.xml."""
    xml_bytes, src = _load_xml_bytes(project_root)
    root = ET.fromstring(xml_bytes)
    zones, by_name = _parse_malaysia_xml(root)
    rso = _parse_rso_zones(by_name, mod_everest, grs80, rso_constants_fn)
    transforms = _parse_transforms(root)
    return zones, rso, transforms
