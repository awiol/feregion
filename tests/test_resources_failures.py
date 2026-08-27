"""Failure and concurrency tests for packaged asset loading."""

import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier, Lock

import numpy as np

import feregion._resources as resources
from feregion.exceptions import DataFileError
from tests.helpers import raises_exact


def _valid_assets() -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    table, names, crosswalk, seismic_names = resources.load_packaged_assets()
    return table.copy(), names.copy(), crosswalk.copy(), seismic_names.copy()


def test_validate_assets_rejects_wrong_table_dtype() -> None:
    """The resource boundary rejects a table that cannot satisfy uint16 storage."""

    table, names, crosswalk, seismic_names = _valid_assets()
    with raises_exact(DataFileError):
        resources._validate_assets(table.astype(np.uint32), names, crosswalk, seismic_names)


def test_validate_assets_rejects_non_unicode_names() -> None:
    """The resource boundary rejects byte-string geographical names."""

    table, names, crosswalk, seismic_names = _valid_assets()
    with raises_exact(DataFileError):
        resources._validate_assets(table, names.astype("S32"), crosswalk, seismic_names)


def test_validate_assets_rejects_missing_active_seismic_mapping() -> None:
    """Every active geographical ID must retain exactly one nonzero seismic parent."""

    table, names, crosswalk, seismic_names = _valid_assets()
    crosswalk[543] = 0
    with raises_exact(DataFileError):
        resources._validate_assets(table, names, crosswalk, seismic_names)


def test_validate_assets_rejects_retired_seismic_mapping() -> None:
    """Retired geographical IDs remain zero sentinels in packaged hierarchy data."""

    table, names, crosswalk, seismic_names = _valid_assets()
    crosswalk[172] = 12
    with raises_exact(DataFileError):
        resources._validate_assets(table, names, crosswalk, seismic_names)


def test_load_packaged_assets_maps_missing_file_to_data_file_error(
    monkeypatch, tmp_path: Path
) -> None:
    """A missing installed asset has a stable package-specific failure class."""

    resources._reset_packaged_assets_cache_for_testing()
    monkeypatch.setattr(resources, "files", lambda package: tmp_path)
    with raises_exact(DataFileError, match="missing"):
        resources.load_packaged_assets()
    resources._reset_packaged_assets_cache_for_testing()


def test_load_packaged_assets_maps_corrupt_npy_to_data_file_error(
    monkeypatch, tmp_path: Path
) -> None:
    """A corrupt installed asset does not leak NumPy's serialization exception."""

    data = tmp_path / "data"
    data.mkdir()
    (data / "fe_table.npy").write_bytes(b"not-an-npy-file")
    resources._reset_packaged_assets_cache_for_testing()
    monkeypatch.setattr(resources, "files", lambda package: tmp_path)
    with raises_exact(DataFileError, match="cannot be read"):
        resources.load_packaged_assets()
    resources._reset_packaged_assets_cache_for_testing()


def test_load_packaged_assets_concurrent_first_use_reads_each_asset_once(
    monkeypatch, tmp_path: Path
) -> None:
    """Concurrent first use performs one read of each of the four runtime assets."""

    data = tmp_path / "data"
    data.mkdir()
    arrays = _valid_assets()
    for filename, array in zip(
        ("fe_table.npy", "fe_names.npy", "fe_seismic_by_geographic.npy", "fe_seismic_names.npy"),
        arrays,
        strict=True,
    ):
        np.save(data / filename, array, allow_pickle=False)

    resources._reset_packaged_assets_cache_for_testing()
    monkeypatch.setattr(resources, "files", lambda package: tmp_path)
    real_load = resources.np.load
    load_calls = 0
    calls_lock = Lock()
    start = Barrier(16)

    def counting_load(*args, **kwargs):
        nonlocal load_calls
        with calls_lock:
            load_calls += 1
        time.sleep(0.01)
        return real_load(*args, **kwargs)

    def load_after_barrier():
        start.wait()
        return resources.load_packaged_assets()

    monkeypatch.setattr(resources.np, "load", counting_load)
    with ThreadPoolExecutor(max_workers=16) as executor:
        results = list(executor.map(lambda _: load_after_barrier(), range(16)))

    assert load_calls == 4
    first = results[0]
    assert all(all(a is b for a, b in zip(result, first, strict=True)) for result in results)
    resources._reset_packaged_assets_cache_for_testing()


def test_validate_assets_rejects_wrong_crosswalk_dtype() -> None:
    """Packaged hierarchy storage is fixed to compact uint8 values."""

    table, names, crosswalk, seismic_names = _valid_assets()
    with raises_exact(DataFileError):
        resources._validate_assets(table, names, crosswalk.astype(np.uint16), seismic_names)


def test_validate_assets_rejects_nonzero_crosswalk_sentinel() -> None:
    """Crosswalk index zero is reserved and must remain zero."""

    table, names, crosswalk, seismic_names = _valid_assets()
    crosswalk[0] = 1
    with raises_exact(DataFileError):
        resources._validate_assets(table, names, crosswalk, seismic_names)


def test_validate_assets_rejects_missing_seismic_identifier() -> None:
    """Packaged hierarchy must retain at least one child for every seismic ID."""

    table, names, crosswalk, seismic_names = _valid_assets()
    crosswalk[crosswalk == 50] = 49
    with raises_exact(DataFileError):
        resources._validate_assets(table, names, crosswalk, seismic_names)


def test_validate_assets_rejects_invalid_seismic_names_shape() -> None:
    """Seismic name storage is one-based with exactly 51 entries."""

    table, names, crosswalk, seismic_names = _valid_assets()
    with raises_exact(DataFileError):
        resources._validate_assets(table, names, crosswalk, seismic_names[:-1])


def test_validate_assets_rejects_empty_active_seismic_name() -> None:
    """Every active seismic ID must resolve to a packaged name."""

    table, names, crosswalk, seismic_names = _valid_assets()
    seismic_names[36] = ""
    with raises_exact(DataFileError):
        resources._validate_assets(table, names, crosswalk, seismic_names)
