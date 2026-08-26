"""Public pandas adapter behavior."""

import numpy as np
import pandas as pd
import pytest

from feregion.exceptions import (
    CoordinateRangeError,
    CoordinateTypeError,
    CoordinateValueError,
    DataFrameColumnError,
    DataFrameTypeError,
)
from feregion.pandas import lookup_dataframe
from tests.helpers import raises_exact


def test_dataframe_adds_region_number_only_by_default() -> None:
    """Default pandas output preserves input data and adds only FE numbers."""

    frame = pd.DataFrame({"longitude": [12.0, -60.0], "latitude": [48.0, -30.0], "x": [1, 2]})
    result = lookup_dataframe(frame)
    assert result is not frame
    assert result["fe_number"].tolist() == [543, 133]
    assert "fe_region" not in result.columns
    assert "fe_number" not in frame.columns


def test_dataframe_can_add_region_names_explicitly() -> None:
    """Name allocation occurs only when include_names is requested."""

    frame = pd.DataFrame({"longitude": [12.0], "latitude": [48.0]})
    result = lookup_dataframe(frame, include_names=True)
    assert result["fe_number"].tolist() == [543]
    assert result["fe_region"].tolist() == ["GERMANY"]


def test_dataframe_supports_custom_coordinate_and_output_columns() -> None:
    """Callers can adapt the pandas interface without renaming source columns."""

    frame = pd.DataFrame({"lon": [12], "lat": [48]})
    result = lookup_dataframe(
        frame,
        longitude_column="lon",
        latitude_column="lat",
        number_column="region_id",
        name_column="region_name",
        include_names=True,
    )
    assert result["region_id"].tolist() == [543]
    assert result["region_name"].tolist() == ["GERMANY"]


def test_dataframe_inplace_mode_returns_and_updates_same_object() -> None:
    """Explicit in-place mode mutates and returns the supplied DataFrame."""

    frame = pd.DataFrame({"longitude": [12.0], "latitude": [48.0]})
    result = lookup_dataframe(frame, inplace=True)
    assert result is frame
    assert frame["fe_number"].tolist() == [543]


def test_dataframe_rejects_missing_longitude_column() -> None:
    """A missing longitude column raises exactly DataFrameColumnError."""

    frame = pd.DataFrame({"latitude": [48.0]})
    with raises_exact(DataFrameColumnError):
        lookup_dataframe(frame)


def test_dataframe_rejects_missing_latitude_column() -> None:
    """A missing latitude column raises exactly DataFrameColumnError."""

    frame = pd.DataFrame({"longitude": [12.0]})
    with raises_exact(DataFrameColumnError):
        lookup_dataframe(frame)


def test_dataframe_rejects_non_numeric_coordinate_column() -> None:
    """Text coordinate columns are not silently coerced by the pandas adapter."""

    frame = pd.DataFrame({"longitude": ["12"], "latitude": [48.0]})
    with raises_exact(CoordinateTypeError):
        lookup_dataframe(frame)


def test_dataframe_nullable_missing_coordinate_uses_core_nonfinite_error() -> None:
    """A numeric pandas missing value is rejected as a non-finite coordinate."""

    frame = pd.DataFrame(
        {
            "longitude": pd.Series([12.0, pd.NA], dtype="Float64"),
            "latitude": pd.Series([48.0, 49.0], dtype="Float64"),
        }
    )
    with raises_exact(CoordinateValueError):
        lookup_dataframe(frame)


def test_dataframe_rejects_non_dataframe_object() -> None:
    """The adapter does not accept duck-typed arbitrary objects as DataFrames."""

    with raises_exact(DataFrameTypeError):
        lookup_dataframe({"longitude": [12.0], "latitude": [48.0]})  # type: ignore[arg-type]


def test_dataframe_rejects_identical_number_and_name_output_columns() -> None:
    """Names cannot overwrite the numeric FE output column."""

    frame = pd.DataFrame({"longitude": [12.0], "latitude": [48.0]})
    with raises_exact(DataFrameColumnError):
        lookup_dataframe(
            frame,
            number_column="region",
            name_column="region",
            include_names=True,
        )


@pytest.mark.parametrize(
    "number_column",
    [
        pytest.param("longitude", id="longitude-coordinate"),
        pytest.param("latitude", id="latitude-coordinate"),
        pytest.param("value", id="existing-unrelated-column"),
    ],
)
def test_dataframe_rejects_region_number_output_collision(number_column: str) -> None:
    """Numeric output never silently replaces coordinate or existing input data."""

    frame = pd.DataFrame({"longitude": [12.0], "latitude": [48.0], "value": [1]})
    with raises_exact(DataFrameColumnError):
        lookup_dataframe(frame, number_column=number_column)


@pytest.mark.parametrize(
    "name_column",
    [
        pytest.param("longitude", id="longitude-coordinate"),
        pytest.param("latitude", id="latitude-coordinate"),
        pytest.param("value", id="existing-unrelated-column"),
    ],
)
def test_dataframe_rejects_region_name_output_collision(name_column: str) -> None:
    """Name output never silently replaces coordinate or existing input data."""

    frame = pd.DataFrame({"longitude": [12.0], "latitude": [48.0], "value": [1]})
    with raises_exact(DataFrameColumnError):
        lookup_dataframe(frame, include_names=True, name_column=name_column)


def test_dataframe_rejects_boolean_coordinate_columns() -> None:
    """The pandas adapter preserves the core rule that Boolean is not a coordinate type."""

    frame = pd.DataFrame({"longitude": [True], "latitude": [False]})
    with raises_exact(CoordinateTypeError):
        lookup_dataframe(frame)


def test_dataframe_rejects_same_coordinate_selector() -> None:
    """One DataFrame column cannot serve as both longitude and latitude."""

    frame = pd.DataFrame({"coordinate": [12.0]})
    with raises_exact(DataFrameColumnError):
        lookup_dataframe(
            frame,
            longitude_column="coordinate",
            latitude_column="coordinate",
        )


def test_dataframe_rejects_duplicate_longitude_label() -> None:
    """Duplicate coordinate labels fail with the package schema exception."""

    frame = pd.DataFrame([[12.0, 13.0, 48.0]], columns=["longitude", "longitude", "latitude"])
    with raises_exact(DataFrameColumnError):
        lookup_dataframe(frame)


def test_dataframe_wide_finite_out_of_range_preserves_core_error_precedence() -> None:
    """Wide pandas floats are range-checked before float64 narrowing.

    The setup uses a finite ``longdouble`` value that overflows ``float64`` on
    platforms where ``longdouble`` has a wider exponent range. The pandas
    adapter must preserve the core batch contract and raise exactly
    ``CoordinateRangeError`` without a narrowing-overflow warning.
    """

    import warnings

    if np.finfo(np.longdouble).max <= np.finfo(np.float64).max:
        pytest.skip("longdouble does not have a wider exponent range than float64")

    frame = pd.DataFrame(
        {
            "longitude": np.array([np.longdouble("1e400")], dtype=np.longdouble),
            "latitude": np.array([0], dtype=np.longdouble),
        }
    )
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        with raises_exact(CoordinateRangeError):
            lookup_dataframe(frame)
