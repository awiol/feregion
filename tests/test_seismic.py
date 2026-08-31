"""FE seismic-region hierarchy and public API contracts."""

from __future__ import annotations

import numpy as np

import feregion
from feregion import FlinnEngdahlLookup
from feregion.exceptions import DataFileError, RegionNumberError, SeismicDataUnavailableError
from tests.helpers import raises_exact


def test_explicit_geographic_aliases_preserve_existing_result() -> None:
    """Canonical geographical names and compatibility names resolve identically."""

    assert feregion.lookup_geographic_number(12.0, 48.0) == feregion.lookup_number(12.0, 48.0)
    assert feregion.geographic_number_to_name(543) == feregion.number_to_name(543)


def test_geographic_region_type_is_canonical_and_region_is_compatibility_alias() -> None:
    """The old Region type remains the geographical type without a migration burden."""

    result = feregion.lookup_region(12.0, 48.0)
    assert isinstance(result, feregion.GeographicRegion)
    assert feregion.Region is feregion.GeographicRegion


def test_scalar_seismic_lookup_is_geographic_lookup_followed_by_crosswalk() -> None:
    """Coordinate-to-seismic behavior is derived from the geographical hierarchy."""

    engine = feregion.get_default_lookup()
    geographic = engine.lookup_geographic_number(12.0, 48.0)
    assert engine.lookup_seismic_number(12.0, 48.0) == engine.geographic_to_seismic_number(
        geographic
    )


def test_batch_seismic_lookup_is_exhaustively_consistent_on_global_cell_centers() -> None:
    """All one-degree cell centers satisfy the hierarchy invariant in one batch."""

    engine = feregion.get_default_lookup()
    longitude = np.arange(-180.0, 180.0) + 0.5
    latitude = np.arange(-90.0, 90.0) + 0.5
    lon_grid, lat_grid = np.meshgrid(longitude, latitude)
    coordinates = np.column_stack((lon_grid.ravel(), lat_grid.ravel()))
    geographic = engine.lookup_geographic_numbers(coordinates)
    expected = engine.geographic_numbers_to_seismic_numbers(geographic)
    np.testing.assert_array_equal(engine.lookup_seismic_numbers(coordinates), expected)


def test_batch_geographic_to_seismic_preserves_shape_and_uint8_dtype() -> None:
    """Hierarchy conversion is vectorized independently of coordinate lookup."""

    numbers = np.array([[543, 133], [1, 757]], dtype=np.uint16)
    result = feregion.geographic_numbers_to_seismic_numbers(numbers)
    assert result.shape == numbers.shape
    assert result.dtype == np.uint8


def test_scalar_array_like_hierarchy_conversion_returns_zero_dimensional_array() -> None:
    """Scalar ArrayLike hierarchy input preserves the public ndarray result contract."""

    result = feregion.geographic_numbers_to_seismic_numbers(543)
    assert type(result) is np.ndarray
    assert result.shape == ()
    assert result.dtype == np.uint8
    assert result.item() == 36


def test_scalar_array_like_seismic_names_returns_zero_dimensional_array() -> None:
    """Scalar ArrayLike seismic-name input returns a zero-dimensional Unicode array."""

    result = feregion.seismic_numbers_to_names(36)
    assert type(result) is np.ndarray
    assert result.shape == ()
    assert result.dtype.kind == "U"
    assert result.item() == "Northwestern Europe"


def test_retired_geographical_number_has_no_seismic_parent() -> None:
    """Storage-range holes are not promoted into active hierarchy members."""

    with raises_exact(RegionNumberError):
        feregion.geographic_to_seismic_number(172)


def test_retired_geographical_numbers_are_not_valid_name_queries() -> None:
    """Historical name slots do not make retired geographical IDs active."""

    for number in (172, 299, 550):
        with raises_exact(RegionNumberError):
            feregion.geographic_number_to_name(number)


def test_retired_geographical_numbers_are_rejected_by_vector_name_lookup() -> None:
    """Vector name lookup applies the same active-ID contract as scalar lookup."""

    numbers = np.asarray([1, 172, 299, 550, 757], dtype=np.uint16)
    with raises_exact(RegionNumberError):
        feregion.geographic_numbers_to_names(numbers)


def test_custom_engine_unused_named_identifier_remains_inactive() -> None:
    """An unused custom name/crosswalk slot cannot create an active region."""

    packaged = feregion.get_default_lookup()
    assert packaged.seismic_by_geographic is not None
    assert packaged.seismic_names is not None
    names = packaged.names.copy()
    names[172] = "HISTORICAL CUSTOM NAME"
    crosswalk = packaged.seismic_by_geographic.copy()
    crosswalk[172] = 12
    engine = FlinnEngdahlLookup(
        packaged.table,
        names,
        crosswalk,
        packaged.seismic_names,
    )

    with raises_exact(RegionNumberError):
        engine.geographic_number_to_name(172)
    with raises_exact(RegionNumberError):
        engine.geographic_to_seismic_number(172)


def test_custom_two_asset_engine_remains_geographical_only() -> None:
    """Existing explicit construction does not silently borrow unrelated hierarchy data."""

    packaged = feregion.get_default_lookup()
    engine = FlinnEngdahlLookup(packaged.table, packaged.names)
    assert engine.lookup_geographic_number(12.0, 48.0) == 543
    assert engine.has_seismic_data is False
    with raises_exact(SeismicDataUnavailableError):
        engine.lookup_seismic_number(12.0, 48.0)


def test_seismic_region_is_immutable_and_named() -> None:
    """Scalar seismic lookup returns its explicit immutable value type."""

    result = feregion.lookup_seismic_region(12.0, 48.0)
    assert result == feregion.SeismicRegion(36, "Northwestern Europe")


def test_explicit_engine_requires_both_seismic_arrays_together() -> None:
    """A partial hierarchy capability declaration is rejected at construction."""

    packaged = feregion.get_default_lookup()
    with raises_exact(DataFileError):
        FlinnEngdahlLookup(packaged.table, packaged.names, packaged.seismic_by_geographic, None)


def test_explicit_engine_rejects_wrong_crosswalk_shape() -> None:
    """Custom hierarchy storage must align one-for-one with geographical names."""

    packaged = feregion.get_default_lookup()
    assert packaged.seismic_names is not None
    with raises_exact(DataFileError):
        FlinnEngdahlLookup(
            packaged.table,
            packaged.names,
            np.zeros(10, dtype=np.uint8),
            packaged.seismic_names,
        )


def test_explicit_engine_rejects_wrong_crosswalk_dtype() -> None:
    """Custom hierarchy storage preserves the compact uint8 contract."""

    packaged = feregion.get_default_lookup()
    assert packaged.seismic_by_geographic is not None
    assert packaged.seismic_names is not None
    with raises_exact(DataFileError):
        FlinnEngdahlLookup(
            packaged.table,
            packaged.names,
            packaged.seismic_by_geographic.astype(np.uint16),
            packaged.seismic_names,
        )


def test_explicit_engine_rejects_nonzero_crosswalk_sentinel() -> None:
    """Custom hierarchy index zero must remain the sentinel."""

    packaged = feregion.get_default_lookup()
    assert packaged.seismic_by_geographic is not None
    assert packaged.seismic_names is not None
    crosswalk = packaged.seismic_by_geographic.copy()
    crosswalk[0] = 1
    with raises_exact(DataFileError):
        FlinnEngdahlLookup(packaged.table, packaged.names, crosswalk, packaged.seismic_names)


def test_explicit_engine_rejects_crosswalk_region_beyond_seismic_names() -> None:
    """A custom hierarchy cannot reference a seismic identifier without a name slot."""

    packaged = feregion.get_default_lookup()
    assert packaged.seismic_by_geographic is not None
    assert packaged.seismic_names is not None
    crosswalk = packaged.seismic_by_geographic.copy()
    crosswalk[543] = packaged.seismic_names.size
    with raises_exact(DataFileError):
        FlinnEngdahlLookup(packaged.table, packaged.names, crosswalk, packaged.seismic_names)


def test_explicit_engine_rejects_missing_active_seismic_mapping() -> None:
    """Every geographical identifier used by the custom table needs a parent."""

    packaged = feregion.get_default_lookup()
    assert packaged.seismic_by_geographic is not None
    assert packaged.seismic_names is not None
    crosswalk = packaged.seismic_by_geographic.copy()
    crosswalk[543] = 0
    with raises_exact(DataFileError):
        FlinnEngdahlLookup(packaged.table, packaged.names, crosswalk, packaged.seismic_names)


def test_explicit_engine_rejects_unnamed_referenced_seismic_region() -> None:
    """Every seismic identifier referenced by the custom crosswalk needs a name."""

    packaged = feregion.get_default_lookup()
    assert packaged.seismic_by_geographic is not None
    assert packaged.seismic_names is not None
    seismic_names = packaged.seismic_names.copy()
    seismic_number = int(packaged.seismic_by_geographic[543])
    seismic_names[seismic_number] = ""
    with raises_exact(DataFileError):
        FlinnEngdahlLookup(
            packaged.table,
            packaged.names,
            packaged.seismic_by_geographic,
            seismic_names,
        )


def test_empty_geographical_hierarchy_conversion_preserves_shape() -> None:
    """An empty valid integer input returns an empty uint8 hierarchy result."""

    result = feregion.geographic_numbers_to_seismic_numbers(np.empty((0, 2), dtype=np.uint16))
    assert result.shape == (0, 2)
    assert result.dtype == np.uint8
