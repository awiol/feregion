"""Load validated binary lookup assets from the installed package."""

from __future__ import annotations

from importlib.resources import files
from threading import Lock

import numpy as np
import numpy.typing as npt

from .exceptions import DataFileError

AssetPair = tuple[npt.NDArray[np.uint16], npt.NDArray[np.str_]]

_assets: AssetPair | None = None
_assets_lock = Lock()


def load_packaged_assets() -> AssetPair:
    """Return one validated, read-only asset pair per Python process.

    Concurrent first callers use a single-flight lock. Exactly one caller reads
    and validates the packaged ``.npy`` files; all other callers reuse that
    result after initialization completes.

    Raises:
        DataFileError: If an asset is missing, unreadable, or structurally
            invalid.
    """

    global _assets
    cached = _assets
    if cached is not None:
        return cached

    with _assets_lock:
        cached = _assets
        if cached is None:
            cached = _read_packaged_assets()
            _assets = cached
        return cached


def _read_packaged_assets() -> AssetPair:
    """Read and validate packaged assets without applying cache policy."""

    data = files("feregion").joinpath("data")
    try:
        with data.joinpath("fe_table.npy").open("rb") as stream:
            table = np.load(stream, allow_pickle=False)
        with data.joinpath("fe_names.npy").open("rb") as stream:
            names = np.load(stream, allow_pickle=False)
    except FileNotFoundError as exc:
        raise DataFileError("packaged Flinn-Engdahl lookup data is missing") from exc
    except (OSError, ValueError) as exc:
        raise DataFileError("packaged Flinn-Engdahl lookup data cannot be read") from exc

    _validate_assets(table, names)
    table.setflags(write=False)
    names.setflags(write=False)
    return table, names


def _reset_packaged_assets_cache_for_testing() -> None:
    """Clear the process cache for deterministic cache-boundary tests."""

    global _assets
    with _assets_lock:
        _assets = None


def _validate_assets(table: np.ndarray, names: np.ndarray) -> None:
    """Check asset structure before a default lookup engine uses it."""

    if table.shape != (4, 91, 181) or table.dtype != np.dtype(np.uint16):
        raise DataFileError(f"invalid lookup table: shape={table.shape}, dtype={table.dtype}")
    if names.ndim != 1 or names.dtype.kind != "U":
        raise DataFileError(f"invalid region names: shape={names.shape}, dtype={names.dtype}")
    if names.size < 2 or names[0] != "":
        raise DataFileError("region names must reserve empty index 0")
    used = np.unique(table)
    if np.any(used == 0) or int(used[-1]) >= names.size or np.any(names[used] == ""):
        raise DataFileError("lookup table references an unknown region number")
