"""Top-level convenience functions and adapter entry points route to the declared contracts."""

from __future__ import annotations

import subprocess
import sys

import numpy as np
import pytest

import feregion
from feregion.exceptions import SeismicDataUnavailableError
from tests.helpers import raises_exact


def test_top_level_geographic_scalar_wrappers_route_to_default_engine() -> None:
    """Explicit and compatibility geographical scalar wrappers preserve their level."""

    assert feregion.lookup_geographic_number(12.0, 48.0) == 543
    assert feregion.lookup_number(12.0, 48.0) == 543
    assert feregion.lookup_geographic_region(12.0, 48.0) == feregion.GeographicRegion(
        543, "GERMANY"
    )
    assert feregion.lookup_region(12.0, 48.0) == feregion.Region(543, "GERMANY")
    assert feregion.geographic_number_to_name(543) == "GERMANY"
    assert feregion.number_to_name(543) == "GERMANY"


def test_top_level_geographic_batch_wrappers_route_to_default_engine() -> None:
    """Explicit and compatibility geographical batch wrappers preserve shape and names."""

    coordinates = np.asarray([[12.0, 48.0], [-60.0, -30.0]])
    expected_numbers = np.asarray([543, 133], dtype=np.uint16)
    np.testing.assert_array_equal(feregion.lookup_geographic_numbers(coordinates), expected_numbers)
    np.testing.assert_array_equal(feregion.lookup_numbers(coordinates), expected_numbers)
    expected_names = np.asarray(["GERMANY", "NORTHEASTERN ARGENTINA"])
    np.testing.assert_array_equal(
        feregion.geographic_numbers_to_names(expected_numbers), expected_names
    )
    np.testing.assert_array_equal(feregion.numbers_to_names(expected_numbers), expected_names)


def test_top_level_seismic_and_hierarchy_wrappers_route_to_default_engine() -> None:
    """Every exported seismic/hierarchy wrapper uses the packaged hierarchy."""

    assert feregion.geographic_to_seismic_number(543) == 36
    np.testing.assert_array_equal(
        feregion.geographic_numbers_to_seismic_numbers(np.asarray([543], dtype=np.uint16)),
        np.asarray([36], dtype=np.uint8),
    )
    assert feregion.lookup_seismic_number(12.0, 48.0) == 36
    assert feregion.lookup_seismic_region(12.0, 48.0) == feregion.SeismicRegion(
        36, "Northwestern Europe"
    )
    np.testing.assert_array_equal(
        feregion.lookup_seismic_numbers(np.asarray([[12.0, 48.0]])),
        np.asarray([36], dtype=np.uint8),
    )
    assert feregion.seismic_number_to_name(36) == "Northwestern Europe"
    np.testing.assert_array_equal(
        feregion.seismic_numbers_to_names(np.asarray([36], dtype=np.uint8)),
        np.asarray(["Northwestern Europe"]),
    )


def test_exported_callable_names_have_direct_routing_coverage() -> None:
    """The expected callable convenience surface remains explicit and reviewable."""

    expected = {
        "get_default_lookup",
        "lookup_geographic_number",
        "lookup_geographic_region",
        "lookup_geographic_numbers",
        "geographic_number_to_name",
        "geographic_numbers_to_names",
        "geographic_to_seismic_number",
        "geographic_numbers_to_seismic_numbers",
        "lookup_seismic_number",
        "lookup_seismic_region",
        "lookup_seismic_numbers",
        "seismic_number_to_name",
        "seismic_numbers_to_names",
        "lookup_number",
        "lookup_region",
        "lookup_numbers",
        "number_to_name",
        "numbers_to_names",
    }
    actual = {name for name in feregion.__all__ if callable(getattr(feregion, name))}
    # Public value types/classes are tested separately; this check guards the
    # convenience-function routing set against an untested addition.
    actual -= {"FlinnEngdahlLookup", "GeographicRegion", "Region", "SeismicRegion"}
    assert actual == expected


def test_python_module_entry_point_routes_to_cli() -> None:
    """``python -m feregion`` exposes the same point lookup contract as the console entry point."""

    completed = subprocess.run(
        [sys.executable, "-m", "feregion", "point", "12", "48", "--level", "seismic"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0
    assert completed.stdout == "36\n"
    assert completed.stderr == ""


def test_public_pandas_routes_both_levels() -> None:
    """The optional pandas adapter explicitly distinguishes geographical and seismic output."""

    pd = pytest.importorskip("pandas")
    from feregion.pandas import lookup_dataframe

    frame = pd.DataFrame({"longitude": [12.0], "latitude": [48.0]})
    geographic = lookup_dataframe(frame, include_names=True)
    seismic = lookup_dataframe(frame, level="seismic", include_names=True)
    assert geographic[["fe_number", "fe_region"]].iloc[0].tolist() == [543, "GERMANY"]
    assert seismic[["fe_seismic_number", "fe_seismic_region"]].iloc[0].tolist() == [
        36,
        "Northwestern Europe",
    ]


def test_public_geojson_routes_generation_and_write(tmp_path) -> None:
    """The optional GeoJSON public functions route level and presentation controls."""

    pytest.importorskip("shapely")
    from feregion.geojson import regions_geojson, write_regions_geojson

    document = regions_geojson(level="seismic", properties=("number",), include_metadata=False)
    assert len(document["features"]) == 50
    output = tmp_path / "regions.geojson"
    write_regions_geojson(
        output,
        level="seismic",
        properties=("number",),
        include_metadata=False,
    )
    assert output.read_text(encoding="utf-8").startswith('{"type": "FeatureCollection"')


def test_geographical_only_engine_rejects_all_public_seismic_operations() -> None:
    """Explicit engines without hierarchy data fail every seismic method explicitly."""

    packaged = feregion.get_default_lookup()
    engine = feregion.FlinnEngdahlLookup(packaged.table, packaged.names)
    with raises_exact(SeismicDataUnavailableError):
        engine.geographic_to_seismic_number(543)
    with raises_exact(SeismicDataUnavailableError):
        engine.geographic_numbers_to_seismic_numbers(np.asarray([543], dtype=np.uint16))
    with raises_exact(SeismicDataUnavailableError):
        engine.lookup_seismic_number(12.0, 48.0)
    with raises_exact(SeismicDataUnavailableError):
        engine.lookup_seismic_region(12.0, 48.0)
    with raises_exact(SeismicDataUnavailableError):
        engine.lookup_seismic_numbers(np.asarray([[12.0, 48.0]]))
    with raises_exact(SeismicDataUnavailableError):
        engine.seismic_number_to_name(36)
    with raises_exact(SeismicDataUnavailableError):
        engine.seismic_numbers_to_names(np.asarray([36], dtype=np.uint8))


def test_explicit_public_function_docstrings_expose_call_contract() -> None:
    """Canonical public functions document inputs, outputs, and owned failures."""

    functions = (
        feregion.lookup_geographic_number,
        feregion.lookup_geographic_region,
        feregion.lookup_geographic_numbers,
        feregion.geographic_number_to_name,
        feregion.geographic_numbers_to_names,
        feregion.geographic_to_seismic_number,
        feregion.geographic_numbers_to_seismic_numbers,
        feregion.lookup_seismic_number,
        feregion.lookup_seismic_region,
        feregion.lookup_seismic_numbers,
        feregion.seismic_number_to_name,
        feregion.seismic_numbers_to_names,
    )
    for function in functions:
        docstring = function.__doc__ or ""
        assert "Args:" in docstring, function.__name__
        assert "Returns:" in docstring, function.__name__
        assert "Raises:" in docstring, function.__name__
