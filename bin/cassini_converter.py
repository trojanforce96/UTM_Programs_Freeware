"""
Coordinate conversion API for EA satellite tools (SHP→DXF, etc.).

Backed by ea_coordinate_wizard — zones load from Malaysia.eap / Malaysia.xml
at import time, same as the Coordinate Wizard.
"""

from ea_coordinate_wizard import (
    ZONES,
    ZONE_NAMES,
    RSO_ZONES,
    packed_dms_to_deg,
    cassini_to_geo,
    mrt48_cassini_to_geo,
    geo_to_cassini,
    geo_to_mrt48_cassini,
    geo_to_rso,
    geo_to_utm,
    utm_zone_from_lon,
    WGS84,
)

from datum_transform import datum_geo_transform, transform_available

__all__ = [
    "ZONES",
    "ZONE_NAMES",
    "packed_dms_to_deg",
    "cassini_to_geo",
    "mrt48_cassini_to_geo",
    "geo_to_utm",
    "utm_zone_from_lon",
    "WGS84",
    "datum_geo_transform",
    "transform_available",
    "cassini_to_latlon",
    "latlon_to_cassini",
    "geo_to_cassini",
    "geo_to_mrt48_cassini",
    "geo_to_rso",
    "RSO_ZONES",
    "find_zone_by_name",
    "rso_zone_for_datum",
]


def find_zone_by_name(zone_name):
    for z in ZONES:
        if z["name"] == zone_name:
            return z
    return None


def rso_zone_for_datum(datum):
    for z in RSO_ZONES:
        if z.get("datum") == datum:
            return z
    raise ValueError(f"No Malaysia RSO definition for datum {datum!r}")


def latlon_to_cassini(zone, lat_deg, lon_deg):
    """Geographic (lat°, lon°) → Cassini grid (N, E metres) in the zone's datum."""
    if zone.get("type") == "C_S" or zone.get("datum") == "MRT48":
        return geo_to_mrt48_cassini(zone, lat_deg, lon_deg)
    return geo_to_cassini(zone, lat_deg, lon_deg)


def cassini_to_latlon(zone, easting, northing):
    """Cassini grid (E, N metres) → (lat°, lon°) in the zone's datum."""
    if zone.get("type") == "C_S" or zone.get("datum") == "MRT48":
        return mrt48_cassini_to_geo(zone, northing, easting)
    return cassini_to_geo(zone, northing, easting)
