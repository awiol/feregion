"""Fast Flinn-Engdahl region lookup for scalar and tabular coordinates."""

from __future__ import annotations

import numpy as np
import numpy.typing as npt

from ._default import get_default_lookup
from .core import FlinnEngdahlLookup
from .types import Region

__version__ = "0.1.1a1"


def lookup_number(longitude: float, latitude: float) -> int:
    """Return one Flinn-Engdahl region number using the cached default engine."""

    return get_default_lookup().lookup_number(longitude, latitude)


def lookup_region(longitude: float, latitude: float) -> Region:
    """Return one slotted :class:`Region` using the cached default engine."""

    return get_default_lookup().lookup_region(longitude, latitude)


def lookup_numbers(coordinates: npt.ArrayLike) -> npt.NDArray[np.uint16]:
    """Return region numbers for a numeric ``(n, 2)`` coordinate array."""

    return get_default_lookup().lookup_numbers(coordinates)


def number_to_name(number: int) -> str:
    """Return the canonical name for one region number."""

    return get_default_lookup().number_to_name(number)


def numbers_to_names(numbers: npt.ArrayLike) -> npt.NDArray[np.str_]:
    """Convert an integer region-number array to a same-shape name array."""

    return get_default_lookup().numbers_to_names(numbers)


__all__ = [
    "FlinnEngdahlLookup",
    "Region",
    "get_default_lookup",
    "lookup_number",
    "lookup_numbers",
    "lookup_region",
    "number_to_name",
    "numbers_to_names",
]
