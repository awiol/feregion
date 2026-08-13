"""Optional lookup-equivalent GeoJSON geometry behavior."""

import numpy as np
import pytest
from shapely.geometry import Point, shape

from feregion import get_default_lookup
from feregion.geojson import regions_geojson

pytestmark = pytest.mark.geo


def test_geojson_has_one_feature_for_each_region_present_in_area_cells() -> None:
    """The feature set exactly covers region numbers assigned to one-degree area cells."""

    engine = get_default_lookup()
    lon = np.arange(-180.0, 180.0) + 0.5
    lat = np.arange(-90.0, 90.0) + 0.5
    lon_grid, lat_grid = np.meshgrid(lon, lat)
    numbers = engine.lookup_numbers(np.column_stack((lon_grid.ravel(), lat_grid.ravel())))
    expected = set(map(int, np.unique(numbers)))
    document = regions_geojson()
    actual = {feature["properties"]["number"] for feature in document["features"]}
    assert document["type"] == "FeatureCollection"
    assert actual == expected


def test_geojson_germany_geometry_covers_germany_reference_cell_center() -> None:
    """A known coordinate center is contained by the feature for its lookup region."""

    document = regions_geojson()
    feature = next(item for item in document["features"] if item["properties"]["number"] == 543)
    geometry = shape(feature["geometry"])
    assert geometry.covers(Point(12.5, 48.5))
    assert feature["properties"]["name"] == "GERMANY"
    assert feature["properties"]["boundary_model"] == "lookup-equivalent 1-degree cells"


def test_write_regions_geojson_serializes_feature_collection(tmp_path) -> None:
    """The file helper writes valid JSON and a final newline."""

    import json

    from feregion.geojson import write_regions_geojson

    output = tmp_path / "regions.geojson"
    write_regions_geojson(output, indent=2)
    text = output.read_text(encoding="utf-8")
    assert text.endswith("\n")
    assert json.loads(text)["type"] == "FeatureCollection"


def test_regions_geojson_maps_missing_shapely_to_custom_dependency_error(monkeypatch) -> None:
    """An unavailable optional geometry dependency has a package-specific exception."""

    import builtins

    from feregion.exceptions import GeoJSONDependencyError
    from tests.helpers import raises_exact

    real_import = builtins.__import__

    def rejecting_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name.startswith("shapely"):
            raise ImportError("shapely intentionally unavailable")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", rejecting_import)
    with raises_exact(GeoJSONDependencyError):
        regions_geojson()


def test_geojson_contains_754_active_features_and_no_retired_regions() -> None:
    """GeoJSON represents active lookup regions and does not invent retired geometry."""

    document = regions_geojson()
    numbers = {feature["properties"]["number"] for feature in document["features"]}
    assert len(numbers) == 754
    assert numbers.isdisjoint({172, 299, 550})
