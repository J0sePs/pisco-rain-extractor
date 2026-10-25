"""Coordinate helpers: UTM to WGS84 conversion and great-circle distance."""

import math

from pyproj import Transformer

UTM_ZONES = (17, 18, 19)  # zones covering Peru
HEMISPHERES = ("North", "South")
EARTH_RADIUS_KM = 6371.0088  # IUGG mean Earth radius


class CoordinateError(ValueError):
    """Invalid coordinate input; the message is shown to the user."""


def utm_to_wgs84(
    easting: float, northing: float, zone: int, hemisphere: str
) -> tuple[float, float]:
    """Convert a UTM coordinate to WGS84 `(longitude, latitude)`, rounded to 6 decimals."""
    if zone not in UTM_ZONES:
        raise CoordinateError("UTM zone must be 17, 18 or 19")
    if hemisphere not in HEMISPHERES:
        raise CoordinateError("Hemisphere must be North or South")
    epsg = (32700 if hemisphere == "South" else 32600) + zone
    transformer = Transformer.from_crs(f"EPSG:{epsg}", "EPSG:4326", always_xy=True)
    lon, lat = transformer.transform(easting, northing)
    return round(lon, 6), round(lat, 6)


def haversine_km(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    """Great-circle distance in km between two WGS84 points (spherical Earth)."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = phi2 - phi1
    d_lambda = math.radians(lon2 - lon1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(a))
