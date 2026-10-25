import pytest

from app.services.coordinates import CoordinateError, haversine_km, utm_to_wgs84


def test_reference_utm_conversion() -> None:
    assert utm_to_wgs84(376135.41, 8640719.67, 18, "South") == (-76.139022, -12.293586)


def test_zone_outside_peru() -> None:
    with pytest.raises(CoordinateError, match="UTM zone must be 17, 18 or 19"):
        utm_to_wgs84(376135.41, 8640719.67, 20, "South")


def test_invalid_hemisphere() -> None:
    with pytest.raises(CoordinateError, match="Hemisphere must be North or South"):
        utm_to_wgs84(376135.41, 8640719.67, 18, "East")


def test_north_hemisphere_uses_northern_crs() -> None:
    # Same easting/northing in the northern zone lands in the northern hemisphere.
    lon, lat = utm_to_wgs84(500000.0, 100000.0, 18, "North")
    assert lat > 0
    assert lon == pytest.approx(-75.0, abs=1e-6)  # central meridian of zone 18


def test_reference_distance() -> None:
    assert round(haversine_km(-76.1390222, -12.2935861, -76.15, -12.25), 3) == 4.991


def test_identical_points() -> None:
    assert round(haversine_km(-76.15, -12.25, -76.15, -12.25), 3) == 0.0
