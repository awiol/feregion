"""Exhaustive coordinate-to-grid-index tests for FE one-degree boundaries.

These tests verify the coordinate-indexing mechanism independently from the
real Flinn-Engdahl region table. Expected table positions come from enumerated
world cells and integer grid boundaries, not from applying the production
``abs``/integer-conversion algorithm to the generated floating-point values.

Three probe engines expose quadrant, absolute-latitude index, and
absolute-longitude index separately. This prevents two adjacent real FE cells
with the same region number from hiding an indexing defect.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pytest

from feregion.core import FlinnEngdahlLookup

_TABLE_SHAPE = (4, 91, 181)


@dataclass(frozen=True, slots=True)
class _AxisProbes:
    """Floating-point probes and their independently constructed axis ownership."""

    values: np.ndarray
    negative_side: np.ndarray
    absolute_index: np.ndarray


@pytest.fixture(scope="module")
def grid_index_probe_engines() -> tuple[FlinnEngdahlLookup, ...]:
    """Return engines that expose each selected dense-table index independently.

    The quadrant probe stores ``quadrant + 1``. The latitude and longitude
    probes store ``absolute_index + 1``. All stored values fit comfortably in
    ``uint16`` and satisfy normal engine data invariants. No probe attempts to
    encode the full 65,884-position dense table into globally unique ``uint16``
    region numbers.
    """

    quadrant = np.broadcast_to(np.arange(1, 5, dtype=np.uint16)[:, None, None], _TABLE_SHAPE).copy()
    latitude = np.broadcast_to(
        np.arange(1, 92, dtype=np.uint16)[None, :, None], _TABLE_SHAPE
    ).copy()
    longitude = np.broadcast_to(
        np.arange(1, 182, dtype=np.uint16)[None, None, :], _TABLE_SHAPE
    ).copy()

    def engine(table: np.ndarray) -> FlinnEngdahlLookup:
        """Build one valid geographical-only engine for a probe table."""

        names = np.asarray([""] + [f"PROBE_{number}" for number in range(1, 183)])
        return FlinnEngdahlLookup(table=table, names=names)

    return engine(quadrant), engine(latitude), engine(longitude)


def _dtype_cases() -> list[object]:
    """Return floating dtypes that add distinct representable-boundary evidence."""

    cases: list[object] = [
        pytest.param(np.float16, id="float16"),
        pytest.param(np.float32, id="float32"),
        pytest.param(np.float64, id="float64"),
    ]
    cases.append(
        pytest.param(
            np.longdouble,
            id="longdouble",
            marks=pytest.mark.skipif(
                np.finfo(np.longdouble).nmant <= np.finfo(np.float64).nmant,
                reason="platform longdouble is not wider than float64",
            ),
        )
    )
    return cases


def _cell_axis_ownership(lower: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Return sign-side and absolute index from integer world-cell identities.

    ``lower`` contains the signed lower integer degree of an area cell. A
    negative cell such as longitude ``[-10, -9)`` belongs to absolute index 9;
    a non-negative cell such as ``[9, 10)`` belongs to index 9. This mapping is
    defined from cell identity before any floating-point test coordinate is
    constructed.
    """

    negative = lower < 0
    absolute_index = np.where(negative, -lower - 1, lower).astype(np.uint16)
    return negative, absolute_index


def _cell_interior_corpus(dtype: type[np.floating]) -> tuple[np.ndarray, ...]:
    """Generate nine strictly interior representable points for every area cell.

    For each of the 64,800 one-degree world cells, the corpus contains the
    Cartesian product of three longitude and three latitude positions: the
    representable value immediately inside the lower edge, the half-degree
    center, and the representable value immediately inside the upper edge.
    The expected quadrant and absolute indices come from the enumerated cell
    identity and therefore do not depend on production float-to-index logic.
    """

    lon_lower_int = np.arange(-180, 180, dtype=np.int16)
    lat_lower_int = np.arange(-90, 90, dtype=np.int16)
    lon_negative, lon_index = _cell_axis_ownership(lon_lower_int)
    lat_negative, lat_index = _cell_axis_ownership(lat_lower_int)

    lon_lower = lon_lower_int.astype(dtype)
    lat_lower = lat_lower_int.astype(dtype)
    one = dtype(1)
    half = dtype("0.5")

    longitude_positions = (
        np.nextafter(lon_lower, lon_lower + one),
        lon_lower + half,
        np.nextafter(lon_lower + one, lon_lower),
    )
    latitude_positions = (
        np.nextafter(lat_lower, lat_lower + one),
        lat_lower + half,
        np.nextafter(lat_lower + one, lat_lower),
    )

    coordinate_parts: list[np.ndarray] = []
    quadrant_parts: list[np.ndarray] = []
    latitude_index_parts: list[np.ndarray] = []
    longitude_index_parts: list[np.ndarray] = []

    expected_quadrant = lon_negative[None, :].astype(np.uint8) + 2 * lat_negative[:, None].astype(
        np.uint8
    )
    expected_latitude = np.broadcast_to(lat_index[:, None], expected_quadrant.shape)
    expected_longitude = np.broadcast_to(lon_index[None, :], expected_quadrant.shape)

    for latitude_values in latitude_positions:
        for longitude_values in longitude_positions:
            longitude_grid, latitude_grid = np.meshgrid(longitude_values, latitude_values)
            coordinate_parts.append(
                np.column_stack((longitude_grid.ravel(), latitude_grid.ravel()))
            )
            quadrant_parts.append(expected_quadrant.ravel())
            latitude_index_parts.append(expected_latitude.ravel())
            longitude_index_parts.append(expected_longitude.ravel())

    return (
        np.concatenate(coordinate_parts),
        np.concatenate(quadrant_parts),
        np.concatenate(latitude_index_parts),
        np.concatenate(longitude_index_parts),
    )


def _longitude_boundary_probes(dtype: type[np.floating]) -> _AxisProbes:
    """Construct previous/exact/next values around every longitude boundary."""

    values: list[np.floating] = []
    negative_side: list[bool] = []
    absolute_index: list[int] = []

    for boundary in range(-180, 181):
        exact = dtype(boundary)
        if boundary > -180:
            lower = boundary - 1
            negative, index = _cell_axis_ownership(np.asarray([lower], dtype=np.int16))
            values.append(np.nextafter(exact, dtype(lower)))
            negative_side.append(bool(negative[0]))
            absolute_index.append(int(index[0]))

        values.append(exact)
        if boundary in (-180, 180):
            # The package contract identifies exact -180 with +180.
            negative_side.append(False)
            absolute_index.append(180)
        elif boundary < 0:
            negative_side.append(True)
            absolute_index.append(-boundary)
        else:
            negative_side.append(False)
            absolute_index.append(boundary)

        if boundary < 180:
            lower = boundary
            negative, index = _cell_axis_ownership(np.asarray([lower], dtype=np.int16))
            values.append(np.nextafter(exact, dtype(boundary + 1)))
            negative_side.append(bool(negative[0]))
            absolute_index.append(int(index[0]))

    return _AxisProbes(
        values=np.asarray(values, dtype=dtype),
        negative_side=np.asarray(negative_side, dtype=np.bool_),
        absolute_index=np.asarray(absolute_index, dtype=np.uint16),
    )


def _latitude_boundary_probes(dtype: type[np.floating]) -> _AxisProbes:
    """Construct previous/exact/next values around every latitude boundary."""

    values: list[np.floating] = []
    negative_side: list[bool] = []
    absolute_index: list[int] = []

    for boundary in range(-90, 91):
        exact = dtype(boundary)
        if boundary > -90:
            lower = boundary - 1
            negative, index = _cell_axis_ownership(np.asarray([lower], dtype=np.int16))
            values.append(np.nextafter(exact, dtype(lower)))
            negative_side.append(bool(negative[0]))
            absolute_index.append(int(index[0]))

        values.append(exact)
        if boundary == -90:
            negative_side.append(True)
            absolute_index.append(90)
        elif boundary == 90:
            negative_side.append(False)
            absolute_index.append(90)
        elif boundary < 0:
            negative_side.append(True)
            absolute_index.append(-boundary)
        else:
            negative_side.append(False)
            absolute_index.append(boundary)

        if boundary < 90:
            lower = boundary
            negative, index = _cell_axis_ownership(np.asarray([lower], dtype=np.int16))
            values.append(np.nextafter(exact, dtype(boundary + 1)))
            negative_side.append(bool(negative[0]))
            absolute_index.append(int(index[0]))

    return _AxisProbes(
        values=np.asarray(values, dtype=dtype),
        negative_side=np.asarray(negative_side, dtype=np.bool_),
        absolute_index=np.asarray(absolute_index, dtype=np.uint16),
    )


def _grid_vertex_corpus(dtype: type[np.floating]) -> tuple[np.ndarray, ...]:
    """Generate representable 3x3 neighborhoods around every integer grid vertex.

    The longitude probe set contains the valid previous/exact/next value at
    every integer longitude boundary. The latitude probe set does the same for
    every integer latitude boundary. Their Cartesian product therefore covers
    every grid intersection and all valid combinations immediately around it.
    """

    longitude = _longitude_boundary_probes(dtype)
    latitude = _latitude_boundary_probes(dtype)
    longitude_grid, latitude_grid = np.meshgrid(longitude.values, latitude.values)
    coordinates = np.column_stack((longitude_grid.ravel(), latitude_grid.ravel()))

    expected_quadrant = longitude.negative_side[None, :].astype(
        np.uint8
    ) + 2 * latitude.negative_side[:, None].astype(np.uint8)
    expected_latitude = np.broadcast_to(latitude.absolute_index[:, None], expected_quadrant.shape)
    expected_longitude = np.broadcast_to(longitude.absolute_index[None, :], expected_quadrant.shape)
    return (
        coordinates,
        expected_quadrant.ravel(),
        expected_latitude.ravel(),
        expected_longitude.ravel(),
    )


def _assert_index_probes(
    engines: tuple[FlinnEngdahlLookup, ...],
    corpus: tuple[np.ndarray, ...],
) -> None:
    """Assert independent quadrant, latitude-index, and longitude-index probes."""

    coordinates, expected_quadrant, expected_latitude, expected_longitude = corpus
    quadrant_engine, latitude_engine, longitude_engine = engines
    np.testing.assert_array_equal(
        quadrant_engine.lookup_geographic_numbers(coordinates), expected_quadrant + 1
    )
    np.testing.assert_array_equal(
        latitude_engine.lookup_geographic_numbers(coordinates), expected_latitude + 1
    )
    np.testing.assert_array_equal(
        longitude_engine.lookup_geographic_numbers(coordinates), expected_longitude + 1
    )


@pytest.mark.parametrize("dtype", _dtype_cases())
def test_every_degree_cell_preserves_index_ownership_at_representable_interior_extremes(
    grid_index_probe_engines: tuple[FlinnEngdahlLookup, ...],
    dtype: type[np.floating],
) -> None:
    """Every area cell keeps its table indices from center to nearest edge values."""

    _assert_index_probes(grid_index_probe_engines, _cell_interior_corpus(dtype))


@pytest.mark.parametrize("dtype", _dtype_cases())
def test_every_grid_vertex_has_correct_previous_exact_next_index_semantics(
    grid_index_probe_engines: tuple[FlinnEngdahlLookup, ...],
    dtype: type[np.floating],
) -> None:
    """Every integer grid corner selects the required indices on all nearby sides."""

    _assert_index_probes(grid_index_probe_engines, _grid_vertex_corpus(dtype))
