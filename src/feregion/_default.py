"""Process-wide default lookup engine."""

from threading import Lock

from ._resources import load_packaged_assets
from .core import FlinnEngdahlLookup

_default_lookup: FlinnEngdahlLookup | None = None
_default_lookup_lock = Lock()


def get_default_lookup() -> FlinnEngdahlLookup:
    """Return exactly one immutable default lookup engine per Python process."""

    global _default_lookup
    cached = _default_lookup
    if cached is not None:
        return cached
    with _default_lookup_lock:
        cached = _default_lookup
        if cached is None:
            table, names, seismic_by_geographic, seismic_names = load_packaged_assets()
            cached = FlinnEngdahlLookup(
                table=table,
                names=names,
                seismic_by_geographic=seismic_by_geographic,
                seismic_names=seismic_names,
            )
            _default_lookup = cached
        return cached


def _reset_default_lookup_cache_for_testing() -> None:
    """Clear the process cache for deterministic cache-boundary tests."""

    global _default_lookup
    with _default_lookup_lock:
        _default_lookup = None
