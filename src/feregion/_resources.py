"""Load validated binary lookup assets from the installed package."""

from __future__ import annotations

from importlib.resources import files
from threading import Lock

import numpy as np
import numpy.typing as npt

from .exceptions import DataFileError

AssetBundle = tuple[
    npt.NDArray[np.uint16],
    npt.NDArray[np.str_],
    npt.NDArray[np.uint8],
    npt.NDArray[np.str_],
]

_assets: AssetBundle | None = None
_assets_lock = Lock()


def load_packaged_assets() -> AssetBundle:
    """Return one validated, read-only runtime asset bundle per process."""

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


def _read_packaged_assets() -> AssetBundle:
    """Read and validate packaged assets without applying cache policy."""

    data = files("feregion").joinpath("data")
    try:
        with data.joinpath("fe_table.npy").open("rb") as stream:
            table = np.load(stream, allow_pickle=False)
        with data.joinpath("fe_names.npy").open("rb") as stream:
            names = np.load(stream, allow_pickle=False)
        with data.joinpath("fe_seismic_by_geographic.npy").open("rb") as stream:
            seismic_by_geographic = np.load(stream, allow_pickle=False)
        with data.joinpath("fe_seismic_names.npy").open("rb") as stream:
            seismic_names = np.load(stream, allow_pickle=False)
    except FileNotFoundError as exc:
        raise DataFileError("packaged Flinn-Engdahl lookup data is missing") from exc
    except (OSError, ValueError) as exc:
        raise DataFileError("packaged Flinn-Engdahl lookup data cannot be read") from exc

    _validate_assets(table, names, seismic_by_geographic, seismic_names)
    for array in (table, names, seismic_by_geographic, seismic_names):
        array.setflags(write=False)
    return table, names, seismic_by_geographic, seismic_names


def _reset_packaged_assets_cache_for_testing() -> None:
    """Clear the process cache for deterministic cache-boundary tests."""

    global _assets
    with _assets_lock:
        _assets = None


def _validate_assets(
    table: np.ndarray,
    names: np.ndarray,
    seismic_by_geographic: np.ndarray,
    seismic_names: np.ndarray,
) -> None:
    """Check packaged geographical and seismic asset invariants."""

    if table.shape != (4, 91, 181) or table.dtype != np.dtype(np.uint16):
        raise DataFileError(f"invalid lookup table: shape={table.shape}, dtype={table.dtype}")
    if names.shape != (758,) or names.dtype.kind != "U" or names[0] != "":
        raise DataFileError(f"invalid geographical names: shape={names.shape}, dtype={names.dtype}")
    used = np.unique(table)
    if np.any(used == 0) or int(used[-1]) >= names.size or np.any(names[used] == ""):
        raise DataFileError("lookup table references an unknown geographical region number")
    if len(used) != 754 or set(map(int, used)).intersection({172, 299, 550}):
        raise DataFileError("lookup table does not contain exactly the active FE geographical IDs")

    if seismic_by_geographic.shape != (758,) or seismic_by_geographic.dtype != np.dtype(np.uint8):
        raise DataFileError(
            "invalid geographical-to-seismic crosswalk: "
            f"shape={seismic_by_geographic.shape}, dtype={seismic_by_geographic.dtype}"
        )
    if seismic_by_geographic[0] != 0:
        raise DataFileError("seismic crosswalk must reserve index 0")
    if any(int(seismic_by_geographic[number]) != 0 for number in (172, 299, 550)):
        raise DataFileError("retired geographical IDs must have seismic sentinel value 0")
    if np.any(seismic_by_geographic[used] == 0):
        raise DataFileError("seismic crosswalk omits an active geographical region")
    mapped = np.unique(seismic_by_geographic[used])
    if not np.array_equal(mapped, np.arange(1, 51, dtype=np.uint8)):
        raise DataFileError("seismic crosswalk must represent every seismic region 1 through 50")

    if seismic_names.shape != (51,) or seismic_names.dtype.kind != "U" or seismic_names[0] != "":
        raise DataFileError(
            f"invalid seismic names: shape={seismic_names.shape}, dtype={seismic_names.dtype}"
        )
    if np.any(seismic_names[1:] == ""):
        raise DataFileError("every seismic region must have a packaged name")
