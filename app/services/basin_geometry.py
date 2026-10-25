"""Basin uploads: read GeoJSON or zipped Shapefiles in memory, validate and dissolve them.

The uploaded bytes are never written to disk (ADR-0018). Validation order and messages follow
design D2; centroid and area follow ADR-0016. No FastAPI and no NetCDF access.
"""

import io
import math
import zipfile
from dataclasses import dataclass
from pathlib import PurePosixPath

import geopandas as gpd
import shapely
from pyproj import Geod, Transformer
from shapely.geometry.base import BaseGeometry

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_ZIP_MEMBERS = 50
MAX_ZIP_UNCOMPRESSED_BYTES = 100 * 1024 * 1024
MAX_FILENAME_LENGTH = 100
GEOJSON_EXTENSIONS = (".geojson", ".json")
SHAPEFILE_PARTS = (".shp", ".shx", ".dbf", ".prj")
POLYGON_TYPES = {"Polygon", "MultiPolygon"}

UNSUPPORTED_MESSAGE = (
    "Unsupported file type: upload a GeoJSON (.geojson, .json) or a zipped Shapefile (.zip)"
)
NO_PRJ_MESSAGE = (
    "The Shapefile has no .prj file, so its coordinate system is unknown. "
    "Include the .prj file in the ZIP."
)

_GEOD = Geod(ellps="WGS84")


class BasinInputError(ValueError):
    """Invalid basin upload; the message is shown to the user."""


@dataclass(frozen=True)
class BasinGeometry:
    """A validated basin: WGS84, dissolved into one geometry."""

    filename: str
    features: int
    geometry: BaseGeometry


def parse_basin_file(filename: str, content: bytes) -> BasinGeometry:
    """Validate and read an uploaded basin file (design D2 order); raises `BasinInputError`."""
    name = _base_name(filename)
    if not name:
        raise BasinInputError("Choose a basin file to upload")
    suffix = PurePosixPath(name.lower()).suffix
    if suffix not in (*GEOJSON_EXTENSIONS, ".zip"):
        raise BasinInputError(UNSUPPORTED_MESSAGE)
    if len(content) > MAX_UPLOAD_BYTES:
        raise BasinInputError("The file is larger than 10 MB")
    is_zip = suffix == ".zip"
    if is_zip:
        _check_zip(content)
    frame = _read(content, "a zipped Shapefile" if is_zip else "GeoJSON")
    frame = _to_wgs84(frame, is_zip)
    geometries = _polygons(frame)
    return BasinGeometry(
        filename=name, features=len(geometries), geometry=shapely.union_all(geometries)
    )


def geodesic_area_km2(geometry: BaseGeometry) -> float:
    """Area on the WGS84 ellipsoid in km², rounded to 1 decimal (ADR-0016)."""
    area, _ = _GEOD.geometry_area_perimeter(geometry)
    return round(abs(area) / 1e6, 1)


def utm_epsg(geometry: BaseGeometry) -> int:
    """Southern-hemisphere UTM EPSG code of the zone holding the center of the bounds."""
    west, _, east, _ = geometry.bounds
    zone = math.floor(((west + east) / 2 + 180) / 6) + 1
    return 32700 + zone


def utm_centroid(geometry: BaseGeometry) -> tuple[float, float]:
    """Centroid computed in UTM and returned as WGS84 `(longitude, latitude)` (ADR-0016)."""
    epsg = utm_epsg(geometry)
    forward = Transformer.from_crs("EPSG:4326", f"EPSG:{epsg}", always_xy=True)
    backward = Transformer.from_crs(f"EPSG:{epsg}", "EPSG:4326", always_xy=True)
    centroid = shapely.transform(geometry, forward.transform, interleaved=False).centroid
    lon, lat = backward.transform(centroid.x, centroid.y)
    return float(lon), float(lat)


def _base_name(filename: str) -> str:
    # Browsers may send a full client path; keep only the last component.
    return filename.replace("\\", "/").rsplit("/", 1)[-1].strip()[:MAX_FILENAME_LENGTH]


def _check_zip(content: bytes) -> None:
    try:
        archive = zipfile.ZipFile(io.BytesIO(content))
    except zipfile.BadZipFile:
        raise BasinInputError("The file could not be read as a zipped Shapefile") from None
    with archive:
        members = [info for info in archive.infolist() if not info.is_dir()]
    if any(_unsafe(info.filename) for info in members):
        raise BasinInputError("The ZIP contains an invalid file path")
    if len(members) > MAX_ZIP_MEMBERS:
        raise BasinInputError(f"The ZIP contains more than {MAX_ZIP_MEMBERS} files")
    if sum(info.file_size for info in members) > MAX_ZIP_UNCOMPRESSED_BYTES:
        raise BasinInputError("The ZIP is larger than 100 MB once extracted")
    names = {info.filename.lower() for info in members}
    shapefiles = [name for name in names if name.endswith(".shp")]
    if len(shapefiles) != 1:
        raise BasinInputError("The ZIP must contain exactly one Shapefile")
    stem = shapefiles[0][: -len(".shp")]
    missing = [ext for ext in SHAPEFILE_PARTS if f"{stem}{ext}" not in names]
    if missing == [".prj"]:
        raise BasinInputError(NO_PRJ_MESSAGE)
    if missing:
        raise BasinInputError(
            f"The ZIP must contain .shp, .shx, .dbf and .prj files (missing: {', '.join(missing)})"
        )


def _unsafe(member: str) -> bool:
    parts = member.replace("\\", "/").split("/")
    return member.startswith(("/", "\\")) or ":" in parts[0] or ".." in parts


def _read(content: bytes, kind: str) -> gpd.GeoDataFrame:
    try:
        return gpd.read_file(io.BytesIO(content))
    except Exception:  # GDAL raises several unrelated types for unreadable input
        raise BasinInputError(f"The file could not be read as {kind}") from None


def _to_wgs84(frame: gpd.GeoDataFrame, is_zip: bool) -> gpd.GeoDataFrame:
    if frame.crs is None:
        if is_zip:
            raise BasinInputError("The .prj file does not describe a known coordinate system")
        return frame.set_crs(4326)  # RFC 7946: GeoJSON without a CRS is WGS84
    if frame.crs.to_epsg() == 4326:
        return frame
    return frame.to_crs(4326)


def _polygons(frame: gpd.GeoDataFrame) -> list[BaseGeometry]:
    geometries = [g for g in frame.geometry if g is not None and not g.is_empty]
    if not geometries:
        raise BasinInputError("The file contains no polygon")
    if any(g.geom_type not in POLYGON_TYPES for g in geometries):
        raise BasinInputError("The basin must be a polygon or multipolygon")
    for geometry in geometries:
        if not shapely.is_valid(geometry):
            reason = shapely.is_valid_reason(geometry)
            raise BasinInputError(f"The basin geometry is invalid: {reason}")
    return geometries
