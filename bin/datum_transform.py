"""JUPEM datum transforms — Helmert 7-parameter chains (PKPUP 2021)."""
import math
from collections import deque

GRS80_ELL = {"a": 6378137.0, "f": 1 / 298.257222101}
MRT48_ELL = {"a": 6377304.063, "f": 1 / 300.8017}
WGS84_ELL = {"a": 6378137.0, "f": 1 / 298.257223563}

_TRANSFORMS = {}


def canon_datum(datum):
    """Map UI / legacy datum labels to Malaysia.xml graph keys (JUPEM PKPUP 2021)."""
    if datum == "WGS84":
        # Peninsula: PMGSN94 is the published WGS84 scientific network (Table 1).
        return "PMGSN94"
    if datum == "MRT68":
        return "MRT48"
    return datum


def set_transforms(transforms):
    """Install transform table from Malaysia.xml <Transform> entries."""
    global _TRANSFORMS
    t = dict(transforms)
    # MRT68 ≡ MRT48 in JUPEM figures (xiv); zones in XML use MRT48.
    extra = {}
    for (a, b), p in t.items():
        aliases_a = {a}
        aliases_b = {b}
        if a in ("MRT48", "MRT68"):
            aliases_a = {"MRT48", "MRT68"}
        if b in ("MRT48", "MRT68"):
            aliases_b = {"MRT48", "MRT68"}
        for aa in aliases_a:
            for bb in aliases_b:
                extra[(aa, bb)] = p
    t.update(extra)
    _TRANSFORMS = t


def ellipsoid_for_datum(datum):
    if datum in ("MRT48", "MRT68"):
        return MRT48_ELL
    if datum in ("WGS84", "PMGSN94"):
        return WGS84_ELL
    return GRS80_ELL


def geo_to_ecef_xyz(lat_deg, lon_deg, datum="GDM2000", h=0.0):
    """Geographic → ECEF (X,Y,Z) metres — GNSS / Earth-centred frame."""
    return _geo_to_ecef(ellipsoid_for_datum(datum), lat_deg, lon_deg, h)


def _geo_to_ecef(ell, lat_deg, lon_deg, h=0.0):
    a, f = ell["a"], ell["f"]
    e2 = 2 * f - f ** 2
    phi, lam = math.radians(lat_deg), math.radians(lon_deg)
    sp, cp = math.sin(phi), math.cos(phi)
    sl, cl = math.sin(lam), math.cos(lam)
    n = a / math.sqrt(1 - e2 * sp * sp)
    return ((n + h) * cp * cl, (n + h) * cp * sl, (n * (1 - e2) + h) * sp)


def _ecef_to_geo(ell, x, y, z):
    a, f = ell["a"], ell["f"]
    e2 = 2 * f - f ** 2
    p = math.hypot(x, y)
    lam = math.atan2(y, x)
    phi = math.atan2(z, p * (1 - e2))
    for _ in range(20):
        sp = math.sin(phi)
        n = a / math.sqrt(1 - e2 * sp * sp)
        phi_new = math.atan2(z + e2 * n * sp, p)
        if abs(phi_new - phi) < 1e-14:
            phi = phi_new
            break
        phi = phi_new
    return math.degrees(phi), math.degrees(lam)


def _helmert_ecef(x, y, z, p):
    """Position-vector Helmert — matches PKPUP 2021 Box 7 / Malaysia.xml."""
    rx = math.radians(p["rx"] / 3600.0)
    ry = math.radians(p["ry"] / 3600.0)
    rz = math.radians(p["rz"] / 3600.0)
    s = 1.0 + p["ppm"] * 1e-6
    return (s * (x + rz * y - ry * z) + p["tx"],
            s * (-rz * x + y + rx * z) + p["ty"],
            s * (ry * x - rx * y + z) + p["tz"])


def _transform_graph():
    g = {}
    for a, b in _TRANSFORMS:
        g.setdefault(a, []).append(b)
    return g


def _datum_path(from_datum, to_datum):
    src = canon_datum(from_datum)
    dst = canon_datum(to_datum)
    if src == dst:
        return []
    graph = _transform_graph()
    q = deque([(src, [])])
    seen = {src}
    while q:
        node, path = q.popleft()
        for nxt in graph.get(node, ()):
            step = path + [(node, nxt)]
            if nxt == dst:
                return step
            if nxt not in seen:
                seen.add(nxt)
                q.append((nxt, step))
    return None


def transform_available(from_datum, to_datum):
    return canon_datum(from_datum) == canon_datum(to_datum) or _datum_path(from_datum, to_datum) is not None


def _single_step(lat_deg, lon_deg, from_datum, to_datum, h=0.0):
    p = _TRANSFORMS.get((from_datum, to_datum))
    if p is None:
        raise ValueError(f"No Helmert parameters for {from_datum} → {to_datum}")
    src_ell = ellipsoid_for_datum(from_datum)
    dst_ell = ellipsoid_for_datum(to_datum)
    x, y, z = _geo_to_ecef(src_ell, lat_deg, lon_deg, h)
    x2, y2, z2 = _helmert_ecef(x, y, z, p)
    return _ecef_to_geo(dst_ell, x2, y2, z2)


def datum_geo_transform(lat_deg, lon_deg, from_datum, to_datum, h=0.0):
    """Transform geographic coordinates — multi-hop via published Helmert steps."""
    path = _datum_path(from_datum, to_datum)
    if not path:
        if canon_datum(from_datum) == canon_datum(to_datum):
            return lat_deg, lon_deg
        raise ValueError(f"No transform path for {from_datum} → {to_datum}")
    lat, lon = lat_deg, lon_deg
    for a, b in path:
        lat, lon = _single_step(lat, lon, a, b, h)
    return lat, lon
