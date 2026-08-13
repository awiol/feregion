"""Tests for the immutable Region value type."""

from dataclasses import FrozenInstanceError

from feregion.types import Region
from tests.helpers import raises_exact


def test_region_exposes_number_and_name() -> None:
    """Region preserves the two public FE values supplied by the caller."""

    region = Region(number=543, name="GERMANY")
    assert region.number == 543
    assert region.name == "GERMANY"


def test_region_is_slotted() -> None:
    """Region instances do not allocate a per-instance attribute dictionary."""

    region = Region(number=543, name="GERMANY")
    assert not hasattr(region, "__dict__")


def test_region_is_immutable() -> None:
    """A caller cannot change a Region after construction."""

    region = Region(number=543, name="GERMANY")
    with raises_exact(FrozenInstanceError):
        region.number = 1  # type: ignore[misc]
