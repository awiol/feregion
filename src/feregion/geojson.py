"""Optional GeoJSON generation from the one-degree lookup grid."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np

from ._default import get_default_lookup
from .core import FlinnEngdahlLookup
from .exceptions import GeoJSONDependencyError


def regions_geojson(*, lookup: FlinnEngdahlLookup | None = None) -> dict[str, Any]:
    """Return area-equivalent one-degree Flinn-Engdahl geometry as GeoJSON.

    The geometry is derived from the same one-degree cells used by the lookup
    contract. Adjacent equal cells are first merged into horizontal rectangles,
    then dissolved by region. A region can therefore be a Polygon or a
    MultiPolygon. Dateline-separated parts remain separate in the conventional
    ``[-180, 180]`` longitude representation.

    The output is intended for visualization and cell-area analysis. Closed
    polygons cannot encode the numeric lookup's directional ownership of every
    exact integer boundary line. Use the numeric lookup API for coordinates on
    cell boundaries. This output is not an authoritative FE vector source.

    Raises:
        GeoJSONDependencyError: If Shapely is not installed.
    """

    try:
        from shapely.geometry import box, mapping
        from shapely.ops import unary_union
    except ImportError as exc:
        raise GeoJSONDependencyError(
            "GeoJSON generation requires the optional 'geo' dependency"
        ) from exc

    engine = lookup if lookup is not None else get_default_lookup()
    longitudes = np.arange(-180.0, 180.0, dtype=np.float64) + 0.5
    latitudes = np.arange(-90.0, 90.0, dtype=np.float64) + 0.5
    longitude_grid, latitude_grid = np.meshgrid(longitudes, latitudes)
    coordinates = np.column_stack((longitude_grid.ravel(), latitude_grid.ravel()))
    numbers = engine.lookup_numbers(coordinates).reshape(180, 360)

    rectangles: dict[int, list[Any]] = defaultdict(list)
    for row_index, latitude in enumerate(range(-90, 90)):
        row = numbers[row_index]
        start = 0
        for end in range(1, 361):
            if end == 360 or row[end] != row[start]:
                number = int(row[start])
                west = -180 + start
                east = -180 + end
                rectangles[number].append(box(west, latitude, east, latitude + 1))
                start = end

    features: list[dict[str, Any]] = []
    for number in sorted(rectangles):
        geometry = unary_union(rectangles[number])
        features.append(
            {
                "type": "Feature",
                "properties": {
                    "number": number,
                    "name": engine.number_to_name(number),
                    "boundary_model": "area-equivalent 1-degree cells",
                    "boundary_semantics": (
                        "numeric lookup is authoritative on exact cell boundaries"
                    ),
                },
                "geometry": mapping(geometry),
            }
        )
    return {"type": "FeatureCollection", "features": features}


def write_regions_geojson(
    path: str | Path,
    *,
    lookup: FlinnEngdahlLookup | None = None,
    indent: int | None = None,
) -> None:
    """Write :func:`regions_geojson` output as UTF-8 GeoJSON."""

    destination = Path(path)
    destination.write_text(
        json.dumps(regions_geojson(lookup=lookup), indent=indent, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
