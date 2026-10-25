import ast
from pathlib import Path

import geopandas as gpd
import pytest
from shapely.geometry import LineString, Polygon, box

from app.services import basin_geometry
from app.services.basin_geometry import (
    MAX_UPLOAD_BYTES,
    NO_PRJ_MESSAGE,
    UNSUPPORTED_MESSAGE,
    BasinInputError,
    geodesic_area_km2,
    parse_basin_file,
    utm_centroid,
)
from tests.basin_files import (
    geojson_bytes,
    rectangle_frame,
    rectangle_geojson,
    shapefile_members,
    zip_bytes,
    zipped_shapefile,
)

RECT = (-76.30, -12.40, -76.10, -12.20)


def _rejects(filename: str, content: bytes, message: str) -> None:
    with pytest.raises(BasinInputError) as error:
        parse_basin_file(filename, content)
    assert str(error.value) == message


def _assert_rectangle(geometry: object, rect: tuple[float, float, float, float]) -> None:
    bounds = geometry.bounds  # type: ignore[attr-defined]
    assert bounds == pytest.approx(rect, abs=1e-6)


# --- reading ---------------------------------------------------------------------------------


def test_zipped_shapefile_read_from_bytes(tmp_path: Path) -> None:
    # Design risk (D2): pyogrio must read a zipped Shapefile from memory.
    basin = parse_basin_file("basin.zip", zipped_shapefile(tmp_path, rectangle_frame(*RECT)))
    assert basin.features == 1
    _assert_rectangle(basin.geometry, RECT)


def test_geojson_accepted_case_insensitive() -> None:
    basin = parse_basin_file("basin.GeoJSON", rectangle_geojson(*RECT))
    assert basin.filename == "basin.GeoJSON"
    _assert_rectangle(basin.geometry, RECT)


def test_json_extension_accepted() -> None:
    assert parse_basin_file("basin.json", rectangle_geojson(*RECT)).features == 1


def test_client_path_reduced_to_base_name() -> None:
    basin = parse_basin_file("C:\\Users\\me\\basin.geojson", rectangle_geojson(*RECT))
    assert basin.filename == "basin.geojson"


def test_shapefile_in_utm_reprojected(tmp_path: Path) -> None:
    content = zipped_shapefile(tmp_path, rectangle_frame(*RECT, epsg=32718))
    _assert_rectangle(parse_basin_file("basin.zip", content).geometry, RECT)


def test_geojson_with_declared_crs_reprojected() -> None:
    utm = rectangle_frame(*RECT, epsg=32718).geometry.iloc[0]
    content = geojson_bytes([utm], crs="urn:ogc:def:crs:EPSG::32718")
    _assert_rectangle(parse_basin_file("basin.geojson", content).geometry, RECT)


# --- type and size ---------------------------------------------------------------------------


def test_no_file_chosen() -> None:
    _rejects("", b"", "Choose a basin file to upload")


def test_unsupported_type() -> None:
    _rejects("basin.kml", b"<kml/>", UNSUPPORTED_MESSAGE)


def test_file_over_limit() -> None:
    _rejects("basin.geojson", b" " * (MAX_UPLOAD_BYTES + 1), "The file is larger than 10 MB")


def test_file_at_limit_passes_size_check() -> None:
    content = rectangle_geojson(*RECT)
    padded = content + b" " * (MAX_UPLOAD_BYTES - len(content))
    assert len(padded) == 10_485_760
    assert parse_basin_file("basin.geojson", padded).features == 1


# --- ZIP checks ------------------------------------------------------------------------------


def test_missing_prj(tmp_path: Path) -> None:
    content = zipped_shapefile(tmp_path, rectangle_frame(*RECT), drop=(".prj",))
    _rejects("basin.zip", content, NO_PRJ_MESSAGE)


def test_missing_dbf(tmp_path: Path) -> None:
    content = zipped_shapefile(tmp_path, rectangle_frame(*RECT), drop=(".dbf",))
    _rejects(
        "basin.zip",
        content,
        "The ZIP must contain .shp, .shx, .dbf and .prj files (missing: .dbf)",
    )


def test_two_shapefiles(tmp_path: Path) -> None:
    frame = rectangle_frame(*RECT)
    members = {
        **shapefile_members(tmp_path / "a", frame, stem="a"),
        **shapefile_members(tmp_path / "b", frame, stem="b"),
    }
    _rejects("basin.zip", zip_bytes(members), "The ZIP must contain exactly one Shapefile")


def test_unsafe_member_path(tmp_path: Path) -> None:
    content = zipped_shapefile(
        tmp_path, rectangle_frame(*RECT), rename={"basin.shp": "../basin.shp"}
    )
    _rejects("basin.zip", content, "The ZIP contains an invalid file path")


def test_too_many_members(tmp_path: Path) -> None:
    members = shapefile_members(tmp_path, rectangle_frame(*RECT))
    members.update({f"extra_{i}.txt": b"x" for i in range(47)})
    assert len(members) == 51
    _rejects("basin.zip", zip_bytes(members), "The ZIP contains more than 50 files")


def test_not_a_zip() -> None:
    _rejects("basin.zip", b"hello", "The file could not be read as a zipped Shapefile")


def test_unreadable_projection(tmp_path: Path) -> None:
    content = zipped_shapefile(tmp_path, rectangle_frame(*RECT), prj_text="not a projection")
    _rejects("basin.zip", content, "The .prj file does not describe a known coordinate system")


# --- geometry --------------------------------------------------------------------------------


def test_no_features() -> None:
    _rejects("basin.geojson", geojson_bytes([]), "The file contains no polygon")


def test_only_lines() -> None:
    content = geojson_bytes([LineString([(-76.3, -12.4), (-76.1, -12.2)])])
    _rejects("basin.geojson", content, "The basin must be a polygon or multipolygon")


def test_self_intersecting_polygon() -> None:
    bow_tie = Polygon([(-76.3, -12.4), (-76.1, -12.2), (-76.1, -12.4), (-76.3, -12.2)])
    with pytest.raises(BasinInputError, match="^The basin geometry is invalid"):
        parse_basin_file("basin.geojson", geojson_bytes([bow_tie]))


def test_not_a_geographic_file() -> None:
    _rejects("basin.geojson", b"hello", "The file could not be read as GeoJSON")


def test_adjacent_features_dissolved() -> None:
    content = geojson_bytes(
        [box(-76.30, -12.40, -76.20, -12.20), box(-76.20, -12.40, -76.10, -12.20)]
    )
    basin = parse_basin_file("basin.geojson", content)
    assert basin.features == 2
    assert basin.geometry.geom_type == "Polygon"
    assert basin.geometry.equals(box(*RECT))


# --- area and centroid -----------------------------------------------------------------------


@pytest.mark.parametrize(
    ("rect", "km2"),
    [((-76.40, -12.50, -76.20, -12.30), 481.2), ((-76.14, -12.24, -76.12, -12.22), 4.8)],
)
def test_geodesic_area(rect: tuple[float, float, float, float], km2: float) -> None:
    assert geodesic_area_km2(box(*rect)) == km2


def test_utm_centroid_of_small_square() -> None:
    lon, lat = utm_centroid(box(-76.105, -12.305, -76.095, -12.295))
    assert lon == pytest.approx(-76.10, abs=1e-7)
    assert lat == pytest.approx(-12.30, abs=1e-7)


def test_utm_centroid_uses_zone_of_the_basin() -> None:
    frame = gpd.GeoSeries([box(*RECT)], crs=4326)
    assert basin_geometry.utm_epsg(frame.iloc[0]) == 32718


def test_module_has_no_web_or_netcdf_imports() -> None:
    tree = ast.parse(Path(basin_geometry.__file__).read_text(encoding="utf-8"))
    modules = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    } | {
        (node.module or "").split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    }
    assert not modules & {"fastapi", "xarray", "netCDF4"}
