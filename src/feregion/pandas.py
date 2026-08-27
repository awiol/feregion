"""Optional pandas adapter for Flinn-Engdahl lookup."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from ._default import get_default_lookup
from .core import FlinnEngdahlLookup
from .exceptions import (
    CoordinateTypeError,
    DataFrameColumnError,
    DataFrameTypeError,
    PandasDependencyError,
)

if TYPE_CHECKING:
    import pandas as pd


def lookup_dataframe(
    frame: pd.DataFrame,
    *,
    longitude_column: str = "longitude",
    latitude_column: str = "latitude",
    number_column: str = "fe_number",
    include_names: bool = False,
    name_column: str = "fe_region",
    inplace: bool = False,
    lookup: FlinnEngdahlLookup | None = None,
) -> pd.DataFrame:
    """Add Flinn-Engdahl region data to a pandas DataFrame.

    Region names are not added unless ``include_names`` is true. The default
    operation returns a copy. Set ``inplace`` to update and return ``frame``.
    Numeric coordinate values retain their source NumPy precision until the
    core batch validator has classified finiteness and coordinate range.

    Output columns are additive. They must be distinct from coordinate columns,
    from each other when names are enabled, and from every pre-existing input
    column. The adapter never silently overwrites caller data.

    Returns:
        The annotated copy, or ``frame`` itself when ``inplace`` is true.

    Raises:
        DataFrameTypeError: If ``frame`` is not a pandas DataFrame.
        DataFrameColumnError: If required coordinate columns are absent or an
            output-column name would collide with input/output schema.
        PandasDependencyError: If pandas is not installed.
        CoordinateTypeError: If a coordinate column is not numeric.
        CoordinateValueError: If a coordinate is NaN or infinite.
        CoordinateRangeError: If a coordinate is outside the valid range.
    """

    try:
        import pandas as pd
        from pandas.api.types import is_bool_dtype, is_numeric_dtype
    except ImportError as exc:  # pragma: no cover - packaging boundary
        raise PandasDependencyError(
            "pandas support requires the optional 'pandas' dependency"
        ) from exc

    if not isinstance(frame, pd.DataFrame):
        raise DataFrameTypeError("frame must be a pandas DataFrame")

    if longitude_column == latitude_column:
        raise DataFrameColumnError("longitude and latitude columns must be different")

    for column in (longitude_column, latitude_column):
        occurrences = sum(label == column for label in frame.columns)
        if occurrences > 1:
            raise DataFrameColumnError(f"coordinate column label must be unique: {column}")

    missing = [
        column for column in (longitude_column, latitude_column) if column not in frame.columns
    ]
    if missing:
        raise DataFrameColumnError(f"missing coordinate columns: {', '.join(missing)}")

    _validate_output_columns(
        frame,
        longitude_column=longitude_column,
        latitude_column=latitude_column,
        number_column=number_column,
        include_names=include_names,
        name_column=name_column,
    )

    for column in (longitude_column, latitude_column):
        dtype = frame[column].dtype
        if is_bool_dtype(dtype) or not is_numeric_dtype(dtype):
            raise CoordinateTypeError(f"DataFrame column {column!r} must be numeric")

    target = frame if inplace else frame.copy()
    longitude = _coordinate_values(target[longitude_column])
    latitude = _coordinate_values(target[latitude_column])
    coordinates = np.column_stack((longitude, latitude))
    engine = lookup if lookup is not None else get_default_lookup()
    numbers = engine.lookup_numbers(coordinates)
    target[number_column] = numbers
    if include_names:
        target[name_column] = engine.numbers_to_names(numbers)
    return target


def _coordinate_values(series: pd.Series) -> np.ndarray:
    """Return numeric coordinate values in a NumPy dtype accepted by the core validator.

    pandas nullable numeric extension dtypes can expose an ``object`` array from
    :meth:`Series.to_numpy` on older supported pandas releases.  That array may
    contain ``pd.NA``, which would make the core validator classify an otherwise
    numeric column as an object-type input.  Native NumPy-backed columns retain
    their dtype.  Only numeric extension arrays that materialize as ``object``
    are converted, with missing values represented as ``np.nan`` so the core
    validator preserves its non-finite-coordinate error contract.

    Args:
        series: A pandas Series already validated as numeric and non-Boolean.

    Returns:
        A NumPy array suitable for stacking into the core coordinate matrix.
    """

    values = series.to_numpy(copy=False)
    if values.dtype.kind != "O":
        return values

    numpy_dtype = getattr(series.dtype, "numpy_dtype", None)
    if numpy_dtype is not None and not series.isna().any():
        return series.to_numpy(dtype=numpy_dtype, copy=False)

    return series.to_numpy(dtype=np.float64, na_value=np.nan, copy=False)


def _validate_output_columns(
    frame: pd.DataFrame,
    *,
    longitude_column: str,
    latitude_column: str,
    number_column: str,
    include_names: bool,
    name_column: str,
) -> None:
    """Reject output names that would overwrite or collapse DataFrame fields."""

    coordinate_columns = {longitude_column, latitude_column}
    if number_column in coordinate_columns:
        raise DataFrameColumnError("region-number column must differ from coordinate columns")
    if number_column in frame.columns:
        raise DataFrameColumnError(f"output column already exists: {number_column}")

    if not include_names:
        return
    if name_column == number_column:
        raise DataFrameColumnError("region-number and region-name columns must be different")
    if name_column in coordinate_columns:
        raise DataFrameColumnError("region-name column must differ from coordinate columns")
    if name_column in frame.columns:
        raise DataFrameColumnError(f"output column already exists: {name_column}")
