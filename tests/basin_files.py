"""Build basin upload files (GeoJSON and zipped Shapefiles) in memory for tests.

Synthetic geometries only; no file from `data/` or any real basin is used.
"""

import io
import json
import zipfile
from collections.abc import Iterable
from pathlib import Path

import geopandas as gpd
from shapely.geometry import box, mapping
from shapely.geometry.base import BaseGeometry

SHAPEFILE_PARTS = (".shp", ".shx", ".dbf", ".prj")


def geojson_bytes(geometries: Iterable[BaseGeometry | dict], crs: str | None = None) -> bytes:
    """A FeatureCollection with one feature per geometry (shapely or GeoJSON mapping).

    `crs` adds the legacy `crs` member (for example "urn:ogc:def:crs:EPSG::32718").
    """
    features = [
        {
            "type": "Feature",
            "properties": {"id": i},
            "geometry": g if isinstance(g, dict) else mapping(g),
        }
        for i, g in enumerate(geometries)
    ]
    collection: dict = {"type": "FeatureCollection", "features": features}
    if crs is not None:
        collection["crs"] = {"type": "name", "properties": {"name": crs}}
    return json.dumps(collection).encode("utf-8")


def rectangle_geojson(w: float, s: float, e: float, n: float, features: int = 1) -> bytes:
    """Rectangle (W, S, E, N) in WGS84, split into `features` adjacent vertical strips."""
    step = (e - w) / features
    strips = [box(w + k * step, s, w + (k + 1) * step, n) for k in range(features)]
    return geojson_bytes(strips)


def shapefile_members(directory: Path, gdf: gpd.GeoDataFrame, stem: str = "basin") -> dict:
    """The `.shp`, `.shx`, `.dbf` and `.prj` files of `gdf` as `{name: bytes}`."""
    directory.mkdir(parents=True, exist_ok=True)
    gdf.to_file(directory / f"{stem}.shp")
    return {f"{stem}{ext}": (directory / f"{stem}{ext}").read_bytes() for ext in SHAPEFILE_PARTS}


def zip_bytes(members: dict[str, bytes]) -> bytes:
    """A ZIP archive holding `members` exactly as named."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, content in members.items():
            archive.writestr(name, content)
    return buffer.getvalue()


def zipped_shapefile(
    directory: Path,
    gdf: gpd.GeoDataFrame,
    *,
    drop: tuple[str, ...] = (),
    rename: dict[str, str] | None = None,
    prj_text: str | None = None,
) -> bytes:
    """A zipped Shapefile of `gdf`; `drop` omits parts by extension, `rename` renames members."""
    members = shapefile_members(directory, gdf)
    if prj_text is not None:
        members["basin.prj"] = prj_text.encode("utf-8")
    members = {name: data for name, data in members.items() if Path(name).suffix not in drop}
    for old, new in (rename or {}).items():
        members[new] = members.pop(old)
    return zip_bytes(members)


def rectangle_frame(w: float, s: float, e: float, n: float, epsg: int = 4326) -> gpd.GeoDataFrame:
    """Rectangle (W, S, E, N) given in WGS84, projected to `epsg`."""
    gdf = gpd.GeoDataFrame({"name": ["basin"]}, geometry=[box(w, s, e, n)], crs=4326)
    return gdf if epsg == 4326 else gdf.to_crs(epsg)
