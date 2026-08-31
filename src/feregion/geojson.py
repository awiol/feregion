"""Optional GeoJSON generation from the shared one-degree FE cell grid."""

from __future__ import annotations

import json
from collections import defaultdict
from collections.abc import Sequence
from pathlib import Path
from typing import Any, Literal

import numpy as np

from ._default import _is_default_lookup_instance, get_default_lookup
from .core import FlinnEngdahlLookup
from .exceptions import GeoJSONDependencyError, GeoJSONOptionError, RegionLevelError

RegionLevel = Literal["geographic", "seismic"]
LabelMode = Literal["number", "name", "number-name"]

_GEOGRAPHIC_PROPERTIES = frozenset(
    {
        "number",
        "name",
        "geographic_number",
        "geographic_name",
        "seismic_number",
        "seismic_name",
    }
)
_SEISMIC_PROPERTIES = frozenset(
    {
        "number",
        "name",
        "seismic_number",
        "seismic_name",
        "geographic_numbers",
        "geographic_names",
    }
)
_DEFAULT_PROPERTIES = ("number", "name")


def regions_geojson(
    *,
    level: RegionLevel = "geographic",
    properties: Sequence[str] = _DEFAULT_PROPERTIES,
    label: LabelMode | None = None,
    include_metadata: bool = True,
    lookup: FlinnEngdahlLookup | None = None,
) -> dict[str, Any]:
    """Return area-equivalent FE geographical or seismic geometry as GeoJSON.

    Args:
        level: Geometry level. With the packaged lookup, ``"geographic"``
            produces the 754 active FE geographical regions and ``"seismic"``
            produces the 50 parent seismic regions. With an explicit lookup,
            feature populations follow that engine's active ownership grid and
            hierarchy.
        properties: Feature properties to include. ``number`` and ``name`` are
            relative to ``level``. Explicit cross-level fields are available
            where their meaning is unambiguous. An empty sequence produces
            geometry-only features.
        label: Optional convenience ``label`` property for human-facing map
            renderers. The supported values use the current level's number,
            name, or ``"<number> <name>"`` combination.
        include_metadata: Include one collection-level ``feregion`` metadata
            object. The packaged default engine identifies the FE-1995 scheme and
            revision. Other explicit engines leave those provenance fields null
            while retaining engine-independent coordinate and boundary semantics.
            Disable metadata for a smaller machine-oriented payload.
        lookup: Optional lookup engine. Explicit custom engines are supported.
            Seismic output requires an engine with seismic hierarchy data.

    Returns:
        A GeoJSON FeatureCollection. Numeric point lookup remains authoritative
        on exact integer cell boundaries.

    Raises:
        RegionLevelError: If ``level`` is unsupported.
        GeoJSONOptionError: If a property or label option is invalid.
        GeoJSONDependencyError: If Shapely is not installed.
    """

    if level not in {"geographic", "seismic"}:
        raise RegionLevelError("level must be 'geographic' or 'seismic'")
    selected_properties = _validate_properties(level, properties)
    if label not in {None, "number", "name", "number-name"}:
        raise GeoJSONOptionError("label must be None, 'number', 'name', or 'number-name'")

    try:
        from shapely.geometry import box, mapping
        from shapely.ops import unary_union
    except ImportError as exc:
        raise GeoJSONDependencyError(
            "GeoJSON generation requires the optional 'geo' dependency"
        ) from exc

    engine = lookup if lookup is not None else get_default_lookup()
    numbers = _cell_number_grid(engine, level)

    rectangles: dict[int, list[Any]] = defaultdict(list)
    for row_index, latitude in enumerate(range(-90, 90)):
        row = numbers[row_index]
        start = 0
        for end in range(1, 361):
            if end == 360 or row[end] != row[start]:
                number = int(row[start])
                rectangles[number].append(box(-180 + start, latitude, -180 + end, latitude + 1))
                start = end

    features: list[dict[str, Any]] = []
    for number in sorted(rectangles):
        geometry = unary_union(rectangles[number])
        feature_properties = _feature_properties(
            engine,
            level=level,
            number=number,
            selected=selected_properties,
            label=label,
        )
        features.append(
            {
                "type": "Feature",
                "properties": feature_properties,
                "geometry": mapping(geometry),
            }
        )

    document: dict[str, Any] = {"type": "FeatureCollection", "features": features}
    if include_metadata:
        document["feregion"] = _collection_metadata(engine, level)
    return document


def _collection_metadata(engine: FlinnEngdahlLookup, level: RegionLevel) -> dict[str, Any]:
    """Return truthful collection metadata for the supplied lookup engine."""

    packaged = _is_default_lookup_instance(engine)
    return {
        "scheme": "Flinn-Engdahl" if packaged else None,
        "revision": "1995" if packaged else None,
        "level": level,
        "coordinate_convention": "WGS84 geographic degrees by package convention",
        "crs_transformation": "none",
        "boundary_model": "area-equivalent 1-degree cells",
        "boundary_semantics": "numeric lookup is authoritative on exact cell boundaries",
    }


def _cell_number_grid(engine: FlinnEngdahlLookup, level: RegionLevel) -> np.ndarray:
    """Resolve the global one-degree cell grid at one FE hierarchy level."""

    longitudes = np.arange(-180.0, 180.0, dtype=np.float64) + 0.5
    latitudes = np.arange(-90.0, 90.0, dtype=np.float64) + 0.5
    longitude_grid, latitude_grid = np.meshgrid(longitudes, latitudes)
    coordinates = np.column_stack((longitude_grid.ravel(), latitude_grid.ravel()))
    geographic = engine.lookup_geographic_numbers(coordinates)
    if level == "geographic":
        return geographic.reshape(180, 360)
    return engine.geographic_numbers_to_seismic_numbers(geographic).reshape(180, 360)


def _validate_properties(level: RegionLevel, properties: Sequence[str]) -> tuple[str, ...]:
    """Validate property names while preserving caller-specified order."""

    selected = tuple(properties)
    if len(set(selected)) != len(selected):
        raise GeoJSONOptionError("GeoJSON properties must not contain duplicates")
    allowed = _GEOGRAPHIC_PROPERTIES if level == "geographic" else _SEISMIC_PROPERTIES
    unsupported = [name for name in selected if name not in allowed]
    if unsupported:
        raise GeoJSONOptionError(
            f"unsupported {level} GeoJSON properties: {', '.join(map(str, unsupported))}"
        )
    return selected


def _feature_properties(
    engine: FlinnEngdahlLookup,
    *,
    level: RegionLevel,
    number: int,
    selected: tuple[str, ...],
    label: LabelMode | None,
) -> dict[str, Any]:
    """Build only requested semantic properties for one feature.

    Expensive cross-level collections are resolved only when the caller asks
    for them. This keeps compact machine-oriented GeoJSON generation compact
    in both output and intermediate work.
    """

    result: dict[str, Any] = {}
    need_name = label in {"name", "number-name"}

    if level == "geographic":
        geographic_name: str | None = None
        seismic_number: int | None = None
        seismic_name: str | None = None

        for field in selected:
            if field in {"number", "geographic_number"}:
                result[field] = number
            elif field in {"name", "geographic_name"}:
                if geographic_name is None:
                    geographic_name = engine.geographic_number_to_name(number)
                result[field] = geographic_name
            elif field == "seismic_number":
                if seismic_number is None:
                    seismic_number = engine.geographic_to_seismic_number(number)
                result[field] = seismic_number
            elif field == "seismic_name":
                if seismic_number is None:
                    seismic_number = engine.geographic_to_seismic_number(number)
                if seismic_name is None:
                    seismic_name = engine.seismic_number_to_name(seismic_number)
                result[field] = seismic_name

        if need_name and geographic_name is None:
            geographic_name = engine.geographic_number_to_name(number)
        current_name = geographic_name
    else:
        current_seismic_name: str | None = None
        geographic_numbers: list[int] | None = None

        for field in selected:
            if field in {"number", "seismic_number"}:
                result[field] = number
            elif field in {"name", "seismic_name"}:
                if current_seismic_name is None:
                    current_seismic_name = engine.seismic_number_to_name(number)
                result[field] = current_seismic_name
            elif field in {"geographic_numbers", "geographic_names"}:
                if geographic_numbers is None:
                    geographic_numbers = (
                        engine._active_geographic_numbers_for_seismic(number).astype(int).tolist()
                    )
                if field == "geographic_numbers":
                    result[field] = geographic_numbers
                else:
                    result[field] = [
                        engine.geographic_number_to_name(value) for value in geographic_numbers
                    ]

        if need_name and current_seismic_name is None:
            current_seismic_name = engine.seismic_number_to_name(number)
        current_name = current_seismic_name

    if label == "number":
        result["label"] = str(number)
    elif label == "name":
        assert current_name is not None
        result["label"] = current_name
    elif label == "number-name":
        assert current_name is not None
        result["label"] = f"{number} {current_name}"
    return result


def write_regions_geojson(
    path: str | Path,
    *,
    level: RegionLevel = "geographic",
    properties: Sequence[str] = _DEFAULT_PROPERTIES,
    label: LabelMode | None = None,
    include_metadata: bool = True,
    lookup: FlinnEngdahlLookup | None = None,
    indent: int | None = None,
) -> None:
    """Write configured area-equivalent FE geometry as UTF-8 GeoJSON."""

    destination = Path(path)
    destination.write_text(
        json.dumps(
            regions_geojson(
                level=level,
                properties=properties,
                label=label,
                include_metadata=include_metadata,
                lookup=lookup,
            ),
            indent=indent,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
