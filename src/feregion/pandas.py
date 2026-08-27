"""Optional pandas adapter for Flinn-Engdahl lookup."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal

import numpy as np
import numpy.typing as npt

from ._default import get_default_lookup
from .core import FlinnEngdahlLookup
from .exceptions import (
    CoordinateTypeError,
    DataFrameColumnError,
    DataFrameTypeError,
    PandasDependencyError,
    RegionLevelError,
)

if TYPE_CHECKING:
    import pandas as pd

RegionLevel = Literal["geographic", "seismic"]


def lookup_dataframe(
    frame: pd.DataFrame,
    *,
    longitude_column: str = "longitude",
    latitude_column: str = "latitude",
    level: RegionLevel = "geographic",
    number_column: str | None = None,
    include_names: bool = False,
    name_column: str | None = None,
    inplace: bool = False,
    lookup: FlinnEngdahlLookup | None = None,
) -> pd.DataFrame:
    """Add FE geographical or seismic region data to a pandas DataFrame.

    Args:
        frame: Input pandas DataFrame.
        longitude_column: Column containing longitude values.
        latitude_column: Column containing latitude values.
        level: ``"geographic"`` for geographical regions or ``"seismic"`` for
            seismic regions.
        number_column: Output number column. The level-specific default is
            ``fe_number`` for geographical lookup and ``fe_seismic_number`` for
            seismic lookup.
        include_names: Add the packaged region name when true.
        name_column: Output name column. The level-specific default is
            ``fe_region`` or ``fe_seismic_region``.
        inplace: Update and return ``frame`` instead of a copy.
        lookup: Optional explicit lookup engine.

    Returns:
        The annotated copy, or ``frame`` itself when ``inplace`` is true.

    Raises:
        RegionLevelError: If ``level`` is not supported.
        DataFrameTypeError: If ``frame`` is not a pandas DataFrame.
        DataFrameColumnError: If coordinate selection or output schema is invalid.
        PandasDependencyError: If pandas is not installed.
        CoordinateTypeError: If a coordinate column is not numeric.
    """

    try:
        import pandas as pd
        from pandas.api.types import is_bool_dtype, is_numeric_dtype
    except ImportError as exc:  # pragma: no cover - packaging boundary
        raise PandasDependencyError(
            "pandas support requires the optional 'pandas' dependency"
        ) from exc

    if level not in {"geographic", "seismic"}:
        raise RegionLevelError("level must be 'geographic' or 'seismic'")
    resolved_number_column = number_column or (
        "fe_number" if level == "geographic" else "fe_seismic_number"
    )
    resolved_name_column = name_column or (
        "fe_region" if level == "geographic" else "fe_seismic_region"
    )

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
        number_column=resolved_number_column,
        include_names=include_names,
        name_column=resolved_name_column,
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
    if level == "geographic":
        geographic_numbers = engine.lookup_geographic_numbers(coordinates)
        target[resolved_number_column] = geographic_numbers
        if include_names:
            target[resolved_name_column] = engine.geographic_numbers_to_names(geographic_numbers)
    else:
        seismic_numbers = engine.lookup_seismic_numbers(coordinates)
        target[resolved_number_column] = seismic_numbers
        if include_names:
            target[resolved_name_column] = engine.seismic_numbers_to_names(seismic_numbers)
    return target


def _coordinate_values(series: pd.Series[Any]) -> npt.NDArray[Any]:
    """Return numeric coordinate values in a NumPy dtype accepted by core validation."""

    values = np.asarray(series.to_numpy(copy=False))
    if values.dtype.kind != "O":
        return values
    numpy_dtype = getattr(series.dtype, "numpy_dtype", None)
    if numpy_dtype is not None and not series.isna().any():
        return np.asarray(series.to_numpy(dtype=numpy_dtype, copy=False))
    return np.asarray(series.to_numpy(dtype=np.float64, na_value=np.nan, copy=False))


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
