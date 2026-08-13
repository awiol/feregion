"""Public exception hierarchy for :mod:`feregion`."""


class FlinnEngdahlError(Exception):
    """Base class for errors raised by ``feregion``."""


class CoordinateShapeError(FlinnEngdahlError, ValueError):
    """The coordinate array does not have the required ``(n, 2)`` shape."""


class CoordinateTypeError(FlinnEngdahlError, TypeError):
    """Coordinate input uses an unsupported non-numeric data type."""


class CoordinateValueError(FlinnEngdahlError, ValueError):
    """Coordinate input contains a non-finite numeric value."""


class CoordinateRangeError(FlinnEngdahlError, ValueError):
    """Longitude or latitude is outside the supported Earth coordinate range."""


class RegionNumberError(FlinnEngdahlError, ValueError):
    """A region number cannot be mapped to a Flinn-Engdahl region name."""


class DataFileError(FlinnEngdahlError, RuntimeError):
    """Packaged Flinn-Engdahl lookup data is missing or invalid."""


class DataFrameTypeError(FlinnEngdahlError, TypeError):
    """The pandas adapter received an unsupported object instead of a DataFrame."""


class DataFrameColumnError(FlinnEngdahlError, KeyError):
    """A required pandas DataFrame coordinate column is missing."""


class PandasDependencyError(FlinnEngdahlError, ImportError):
    """The optional pandas dependency is not installed."""


class CsvInputError(FlinnEngdahlError, ValueError):
    """CSV input does not satisfy the command-line input contract."""


class GeoJSONDependencyError(FlinnEngdahlError, ImportError):
    """The optional GeoJSON dependency is not installed."""
