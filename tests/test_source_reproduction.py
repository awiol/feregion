"""Independent checks that generated assets preserve verified source-table semantics."""

import numpy as np
import pytest

from feregion import get_default_lookup
from tests.reference import SourceReference
from tools.build_assets import build_names, build_table
from tools.obspy_fe_source import DEFAULT_SOURCE_DIR, verify_source_dir

SOURCE = DEFAULT_SOURCE_DIR
pytestmark = pytest.mark.integration


def require_source_data() -> None:
    """Skip source-reproduction checks until the pinned upstream data is fetched."""

    try:
        verify_source_dir(SOURCE)
    except FileNotFoundError as exc:
        pytest.skip(str(exc))


def test_regenerated_table_matches_packaged_table() -> None:
    """Running the repository generator recreates the exact numeric table values."""

    require_source_data()

    generated = build_table(SOURCE)
    np.testing.assert_array_equal(generated, get_default_lookup().table)


def test_regenerated_names_match_packaged_names() -> None:
    """Running the repository generator recreates the exact direct name mapping."""

    require_source_data()

    generated = build_names(SOURCE)
    np.testing.assert_array_equal(generated, get_default_lookup().names)


def test_dense_lookup_matches_independent_source_scan_on_complete_integer_grid() -> None:
    """Every supported integer coordinate agrees with a direct source breakpoint scan."""

    require_source_data()

    reference = SourceReference(SOURCE)
    engine = get_default_lookup()
    coordinates = np.array(
        [(lon, lat) for lat in range(-90, 91) for lon in range(-180, 181)],
        dtype=np.float64,
    )
    expected = np.fromiter(
        (reference.number(lon, lat) for lon, lat in coordinates),
        dtype=np.uint16,
        count=coordinates.shape[0],
    )
    actual = engine.lookup_numbers(coordinates)
    np.testing.assert_array_equal(actual, expected)


def test_dense_lookup_matches_independent_source_scan_for_seeded_fractional_sample() -> None:
    """Fractional coordinates agree with the independent reference beyond integer boundaries."""

    require_source_data()

    reference = SourceReference(SOURCE)
    engine = get_default_lookup()
    rng = np.random.default_rng(20260813)
    coordinates = np.column_stack((rng.uniform(-180, 180, 5000), rng.uniform(-90, 90, 5000)))
    expected = np.fromiter(
        (reference.number(lon, lat) for lon, lat in coordinates),
        dtype=np.uint16,
        count=coordinates.shape[0],
    )
    np.testing.assert_array_equal(engine.lookup_numbers(coordinates), expected)


def test_scalar_lookup_matches_independent_source_scan_for_seeded_fractional_sample() -> None:
    """The dedicated scalar path preserves source-table semantics after optimization."""

    require_source_data()

    reference = SourceReference(SOURCE)
    engine = get_default_lookup()
    rng = np.random.default_rng(20260814)
    coordinates = np.column_stack((rng.uniform(-180, 180, 5_000), rng.uniform(-90, 90, 5_000)))

    for longitude, latitude in coordinates:
        assert engine.lookup_number(longitude, latitude) == reference.number(longitude, latitude)
