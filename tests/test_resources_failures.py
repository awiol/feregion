"""Failure and concurrency tests for packaged asset loading."""

import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier, Lock

import numpy as np

import feregion._resources as resources
from feregion.exceptions import DataFileError
from tests.helpers import raises_exact


def _valid_assets() -> tuple[np.ndarray, np.ndarray]:
    table = np.ones((4, 91, 181), dtype=np.uint16)
    names = np.array(["", "ONE"], dtype="<U8")
    return table, names


def test_validate_assets_rejects_wrong_table_dtype() -> None:
    """The resource boundary rejects a table that cannot satisfy uint16 storage."""

    _, names = _valid_assets()
    with raises_exact(DataFileError):
        resources._validate_assets(np.ones((4, 91, 181), dtype=np.uint32), names)


def test_validate_assets_rejects_non_unicode_names() -> None:
    """The resource boundary rejects byte-string names before engine construction."""

    table, _ = _valid_assets()
    with raises_exact(DataFileError):
        resources._validate_assets(table, np.array([b"", b"ONE"], dtype="S8"))


def test_validate_assets_rejects_name_array_without_reserved_zero() -> None:
    """The resource boundary requires the one-based region-name convention."""

    table, _ = _valid_assets()
    with raises_exact(DataFileError):
        resources._validate_assets(table, np.array(["ZERO", "ONE"], dtype="<U8"))


def test_validate_assets_rejects_unknown_table_region() -> None:
    """A region identifier without a direct name mapping is rejected at load time."""

    table, _ = _valid_assets()
    table[0, 0, 0] = 2
    with raises_exact(DataFileError):
        resources._validate_assets(table, np.array(["", "ONE"], dtype="<U8"))


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
    """Concurrent first use performs one pair of NumPy file reads for the process."""

    data = tmp_path / "data"
    data.mkdir()
    table, names = _valid_assets()
    np.save(data / "fe_table.npy", table, allow_pickle=False)
    np.save(data / "fe_names.npy", names, allow_pickle=False)

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

    assert load_calls == 2
    first_table, first_names = results[0]
    assert all(result[0] is first_table and result[1] is first_names for result in results)
    resources._reset_packaged_assets_cache_for_testing()
