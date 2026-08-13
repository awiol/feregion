"""Development-only comparison with the installed ObsPy implementation."""

import numpy as np
import pytest

import feregion

pytestmark = [pytest.mark.integration, pytest.mark.obspy]
obspy = pytest.importorskip("obspy", reason="ObsPy is a development-only oracle")


def test_random_fractional_points_match_obspy_reference() -> None:
    """A deterministic broad sample agrees with an independently installed ObsPy."""

    from obspy.geodetics import FlinnEngdahl

    reference = FlinnEngdahl()
    rng = np.random.default_rng(20260813)
    coordinates = np.column_stack((rng.uniform(-180, 180, 10_000), rng.uniform(-90, 90, 10_000)))
    expected = np.fromiter(
        (reference.get_number(lon, lat) for lon, lat in coordinates),
        dtype=np.uint16,
        count=coordinates.shape[0],
    )
    np.testing.assert_array_equal(feregion.lookup_numbers(coordinates), expected)
