"""Regression coverage for coordinate precision at FE integer-degree boundaries."""

from __future__ import annotations

import numpy as np
import pytest

import feregion


def _wide_longdouble_available() -> bool:
    """Return whether longdouble can represent values between adjacent float64 values."""

    return np.finfo(np.longdouble).nmant > np.finfo(np.float64).nmant


pytestmark = pytest.mark.skipif(
    not _wide_longdouble_available(),
    reason="platform longdouble is not wider than float64",
)


def _boundary_corpus() -> np.ndarray:
    """Return valid longdouble points immediately beside FE degree boundaries.

    The corpus covers both sides of every interior integer longitude and
    latitude boundary, both antimeridian interiors, exact range limits, the
    equator/prime-meridian transitions, and the poles. It is a discontinuity
    regression corpus, not a population sample.
    """

    dtype = np.longdouble
    points: list[tuple[np.longdouble, np.longdouble]] = []

    for degree in range(-179, 180):
        boundary = dtype(degree)
        points.append((np.nextafter(boundary, dtype(-np.inf)), dtype("45.5")))
        points.append((np.nextafter(boundary, dtype(np.inf)), dtype("45.5")))

    for degree in range(-89, 90):
        boundary = dtype(degree)
        points.append((dtype("12.5"), np.nextafter(boundary, dtype(-np.inf))))
        points.append((dtype("12.5"), np.nextafter(boundary, dtype(np.inf))))

    points.extend(
        [
            (np.nextafter(dtype(-180), dtype(0)), dtype("0.5")),
            (np.nextafter(dtype(180), dtype(0)), dtype("0.5")),
            (dtype(-180), dtype("0.5")),
            (dtype(180), dtype("0.5")),
            (dtype("-0.0"), dtype("-0.0")),
            (dtype(0), dtype(90)),
            (dtype(0), dtype(-90)),
        ]
    )
    return np.asarray(points, dtype=dtype)


def test_extended_precision_batch_geographic_matches_scalar_at_degree_boundaries() -> None:
    """Batch lookup preserves source precision until FE cell ownership is selected.

    Predecessor sensitivity: this corpus contains coordinates that fail against
    the 0.2.0a1 implementation because it narrows valid longdouble values to
    float64 before integer-cell indexing.
    """

    coordinates = _boundary_corpus()
    expected = np.fromiter(
        (feregion.lookup_geographic_number(lon, lat) for lon, lat in coordinates),
        dtype=np.uint16,
        count=len(coordinates),
    )
    observed = feregion.lookup_geographic_numbers(coordinates)
    np.testing.assert_array_equal(observed, expected)


def test_extended_precision_batch_seismic_matches_scalar_at_degree_boundaries() -> None:
    """Seismic batch lookup inherits exact scalar cell ownership at discontinuities."""

    coordinates = _boundary_corpus()
    expected = np.fromiter(
        (feregion.lookup_seismic_number(lon, lat) for lon, lat in coordinates),
        dtype=np.uint8,
        count=len(coordinates),
    )
    observed = feregion.lookup_seismic_numbers(coordinates)
    np.testing.assert_array_equal(observed, expected)


def test_pandas_preserved_longdouble_matches_scalar_at_degree_boundary() -> None:
    """pandas routing preserves the corrected core semantics when dtype survives."""

    pd = pytest.importorskip("pandas")
    from feregion.pandas import lookup_dataframe

    longitude = np.asarray(
        [np.longdouble("8.999999999999999999"), np.nextafter(np.longdouble(-180), 0)],
        dtype=np.longdouble,
    )
    latitude = np.asarray([np.longdouble("0.5"), np.longdouble("0.5")], dtype=np.longdouble)
    frame = pd.DataFrame({"longitude": longitude, "latitude": latitude})
    preserved = frame["longitude"].to_numpy(copy=False)
    if preserved.dtype.itemsize <= np.dtype(np.float64).itemsize:
        pytest.skip("pandas does not preserve a wider floating dtype on this platform")

    expected_geographic = [
        feregion.lookup_geographic_number(lon, lat)
        for lon, lat in zip(longitude, latitude, strict=True)
    ]
    expected_seismic = [
        feregion.lookup_seismic_number(lon, lat)
        for lon, lat in zip(longitude, latitude, strict=True)
    ]
    geographic = lookup_dataframe(frame)
    seismic = lookup_dataframe(frame, level="seismic")
    assert geographic["fe_number"].tolist() == expected_geographic
    assert seismic["fe_seismic_number"].tolist() == expected_seismic
