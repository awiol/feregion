"""Optional area-equivalent GeoJSON geometry and presentation behavior."""

import numpy as np
import pytest
from shapely.geometry import Point, shape

from feregion import FlinnEngdahlLookup, get_default_lookup
from feregion.exceptions import GeoJSONOptionError, RegionLevelError
from feregion.geojson import regions_geojson
from tests.helpers import raises_exact

pytestmark = pytest.mark.geo


def test_geographic_geojson_has_one_feature_for_each_active_area_region() -> None:
    """The geographical feature set exactly covers all active one-degree cells."""

    engine = get_default_lookup()
    lon = np.arange(-180.0, 180.0) + 0.5
    lat = np.arange(-90.0, 90.0) + 0.5
    lon_grid, lat_grid = np.meshgrid(lon, lat)
    numbers = engine.lookup_geographic_numbers(
        np.column_stack((lon_grid.ravel(), lat_grid.ravel()))
    )
    expected = set(map(int, np.unique(numbers)))
    document = regions_geojson()
    actual = {feature["properties"]["number"] for feature in document["features"]}
    assert actual == expected


def test_seismic_geojson_has_exactly_fifty_features() -> None:
    """Mapping the shared cell grid through the crosswalk produces 50 parents."""

    document = regions_geojson(level="seismic")
    numbers = {feature["properties"]["number"] for feature in document["features"]}
    assert numbers == set(range(1, 51))


def test_geographic_geojson_germany_geometry_and_collection_metadata() -> None:
    """A known cell is covered and invariant semantics live at collection level."""

    document = regions_geojson()
    feature = next(item for item in document["features"] if item["properties"]["number"] == 543)
    geometry = shape(feature["geometry"])
    assert geometry.covers(Point(12.5, 48.5))
    assert feature["properties"] == {"number": 543, "name": "GERMANY"}
    assert document["feregion"] == {
        "scheme": "Flinn-Engdahl",
        "revision": "1995",
        "level": "geographic",
        "coordinate_convention": "WGS84 geographic degrees by package convention",
        "crs_transformation": "none",
        "boundary_model": "area-equivalent 1-degree cells",
        "boundary_semantics": "numeric lookup is authoritative on exact cell boundaries",
    }


def test_geojson_can_emit_geometry_only_without_collection_metadata() -> None:
    """Machine-oriented output can omit every optional semantic annotation."""

    document = regions_geojson(properties=(), include_metadata=False)
    assert "feregion" not in document
    assert document["features"][0]["properties"] == {}


def test_geographic_geojson_can_add_parent_seismic_properties_and_label() -> None:
    """Human-facing geographical output can expose parent identifiers and a label."""

    document = regions_geojson(
        properties=("geographic_number", "geographic_name", "seismic_number", "seismic_name"),
        label="number-name",
    )
    feature = next(
        item for item in document["features"] if item["properties"]["geographic_number"] == 543
    )
    assert feature["properties"] == {
        "geographic_number": 543,
        "geographic_name": "GERMANY",
        "seismic_number": 36,
        "seismic_name": "Northwestern Europe",
        "label": "543 GERMANY",
    }


def test_seismic_geojson_can_include_geographic_regions() -> None:
    """Seismic output may expose active child regions as number/name objects."""

    document = regions_geojson(
        level="seismic",
        properties=("seismic_number", "seismic_name", "geographic_regions"),
    )
    feature = next(
        item for item in document["features"] if item["properties"]["seismic_number"] == 36
    )
    assert {"number": 543, "name": "GERMANY"} in feature["properties"]["geographic_regions"]


@pytest.mark.parametrize(
    "property_name",
    ["geographic_number", "geographic_name", "geographic_numbers", "geographic_names"],
)
def test_geojson_rejects_level_incompatible_geographic_property(property_name: str) -> None:
    """Seismic features reject scalar or legacy parallel geographical properties."""

    with raises_exact(GeoJSONOptionError):
        regions_geojson(level="seismic", properties=(property_name,))


def test_geojson_rejects_unknown_level() -> None:
    """An unknown hierarchy level has a package-specific contract failure."""

    with raises_exact(RegionLevelError):
        regions_geojson(level="other")  # type: ignore[arg-type]


def test_geojson_rejects_duplicate_properties() -> None:
    """Duplicate output properties are rejected rather than silently collapsed."""

    with raises_exact(GeoJSONOptionError):
        regions_geojson(properties=("number", "number"))


def test_write_regions_geojson_serializes_feature_collection(tmp_path) -> None:
    """The file helper writes configured valid JSON and a final newline."""

    import json

    from feregion.geojson import write_regions_geojson

    output = tmp_path / "regions.geojson"
    write_regions_geojson(
        output,
        level="seismic",
        properties=("number",),
        include_metadata=False,
        indent=2,
    )
    text = output.read_text(encoding="utf-8")
    assert text.endswith("\n")
    document = json.loads(text)
    assert len(document["features"]) == 50


def test_regions_geojson_maps_missing_shapely_to_custom_dependency_error(monkeypatch) -> None:
    """An unavailable optional geometry dependency has a package-specific exception."""

    import builtins

    from feregion.exceptions import GeoJSONDependencyError

    real_import = builtins.__import__

    def rejecting_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name.startswith("shapely"):
            raise ImportError("shapely intentionally unavailable")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", rejecting_import)
    with raises_exact(GeoJSONDependencyError):
        regions_geojson()


def test_geographic_geojson_contains_754_active_features_and_no_retired_regions() -> None:
    """Geographical geometry excludes the three retired identifiers."""

    document = regions_geojson()
    numbers = {feature["properties"]["number"] for feature in document["features"]}
    assert len(numbers) == 754
    assert numbers.isdisjoint({172, 299, 550})


def test_geojson_label_modes_cover_number_and_name() -> None:
    """The two single-field human labels remain available independently."""

    numbered = regions_geojson(properties=(), label="number")
    named = regions_geojson(level="seismic", properties=(), label="name")
    assert numbered["features"][0]["properties"]["label"].isdigit()
    assert named["features"][0]["properties"]["label"] == "Alaska - Aleutian Arc"


def test_geojson_rejects_unknown_label() -> None:
    """The label option is a bounded vocabulary rather than a template language."""

    with raises_exact(GeoJSONOptionError):
        regions_geojson(label="custom")  # type: ignore[arg-type]


def test_geojson_seismic_name_can_be_requested_without_generic_name() -> None:
    """Explicit seismic-name annotation works independently of generic aliases."""

    document = regions_geojson(level="seismic", properties=("seismic_name",))
    assert document["features"][0]["properties"] == {"seismic_name": "Alaska - Aleutian Arc"}


@pytest.mark.parametrize("level", ["geographic", "seismic"])
def test_geojson_covers_every_cell_center_owned_by_numeric_lookup(level: str) -> None:
    """Every global one-degree cell center lies in its numeric lookup feature."""

    from shapely.geometry import MultiPoint

    engine = get_default_lookup()
    longitudes = np.arange(-180.0, 180.0) + 0.5
    latitudes = np.arange(-90.0, 90.0) + 0.5
    longitude_grid, latitude_grid = np.meshgrid(longitudes, latitudes)
    coordinates = np.column_stack((longitude_grid.ravel(), latitude_grid.ravel()))
    geographic = engine.lookup_geographic_numbers(coordinates)
    if level == "geographic":
        numbers = geographic
    else:
        numbers = engine.geographic_numbers_to_seismic_numbers(geographic)

    document = regions_geojson(level=level)
    geometries = {
        int(feature["properties"]["number"]): shape(feature["geometry"])
        for feature in document["features"]
    }
    for number in np.unique(numbers):
        owned = coordinates[numbers == number]
        assert geometries[int(number)].covers(MultiPoint(owned))


def test_custom_hierarchy_geojson_excludes_populated_inactive_crosswalk_slots() -> None:
    """Seismic child properties use the engine's active geographical membership."""

    packaged = get_default_lookup()
    assert packaged.seismic_by_geographic is not None
    assert packaged.seismic_names is not None
    crosswalk = packaged.seismic_by_geographic.copy()
    crosswalk[172] = 1
    engine = FlinnEngdahlLookup(
        packaged.table,
        packaged.names,
        crosswalk,
        packaged.seismic_names,
    )

    document = regions_geojson(
        level="seismic",
        properties=("seismic_number", "geographic_regions"),
        lookup=engine,
        include_metadata=False,
    )
    feature = next(
        item for item in document["features"] if item["properties"]["seismic_number"] == 1
    )
    regions = feature["properties"]["geographic_regions"]

    assert all(region["number"] != 172 for region in regions)
    assert regions == [
        {"number": number, "name": engine.geographic_number_to_name(number)}
        for number in engine._active_geographic_numbers_for_seismic(1).astype(int).tolist()
    ]


def test_custom_hierarchy_unused_crosswalk_slot_does_not_change_geojson_children() -> None:
    """An inactive hierarchy slot cannot change cross-level GeoJSON properties."""

    packaged = get_default_lookup()
    assert packaged.seismic_by_geographic is not None
    assert packaged.seismic_names is not None
    crosswalk = packaged.seismic_by_geographic.copy()
    crosswalk[172] = 1
    engine = FlinnEngdahlLookup(
        packaged.table,
        packaged.names,
        crosswalk,
        packaged.seismic_names,
    )

    expected = regions_geojson(
        level="seismic",
        properties=("seismic_number", "geographic_regions"),
        lookup=packaged,
        include_metadata=False,
    )
    actual = regions_geojson(
        level="seismic",
        properties=("seismic_number", "geographic_regions"),
        lookup=engine,
        include_metadata=False,
    )
    assert actual == expected


def test_custom_geographic_engine_uses_provenance_neutral_collection_metadata() -> None:
    """Custom geometry must not inherit packaged FE-1995 provenance claims."""

    table = np.ones((4, 91, 181), dtype=np.uint16)
    names = np.array(["", "CUSTOM"], dtype=np.str_)
    engine = FlinnEngdahlLookup(table, names)

    document = regions_geojson(lookup=engine)

    assert len(document["features"]) == 1
    assert document["features"][0]["properties"] == {"number": 1, "name": "CUSTOM"}
    assert document["feregion"] == {
        "scheme": None,
        "revision": None,
        "level": "geographic",
        "coordinate_convention": "WGS84 geographic degrees by package convention",
        "crs_transformation": "none",
        "boundary_model": "area-equivalent 1-degree cells",
        "boundary_semantics": "numeric lookup is authoritative on exact cell boundaries",
    }


def test_explicit_packaged_engine_retains_packaged_geojson_metadata() -> None:
    """An explicit engine that matches packaged data retains FE-1995 metadata."""

    implicit = regions_geojson(properties=())
    explicit = regions_geojson(properties=(), lookup=get_default_lookup())
    assert explicit["feregion"] == implicit["feregion"]


def test_custom_hierarchy_engine_uses_provenance_neutral_collection_metadata() -> None:
    """A modified hierarchy must not inherit packaged FE-1995 provenance metadata."""

    packaged = get_default_lookup()
    assert packaged.seismic_by_geographic is not None
    assert packaged.seismic_names is not None
    crosswalk = packaged.seismic_by_geographic.copy()
    crosswalk[172] = 1
    engine = FlinnEngdahlLookup(
        packaged.table,
        packaged.names,
        crosswalk,
        packaged.seismic_names,
    )

    document = regions_geojson(level="seismic", properties=(), lookup=engine)
    assert document["feregion"]["scheme"] is None
    assert document["feregion"]["revision"] is None
