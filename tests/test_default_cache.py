"""Process-wide caching contract for normal package use."""

import time
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Lock

import numpy as np

import feregion._default as default_module


def test_default_lookup_loads_assets_once_and_reuses_one_engine(monkeypatch) -> None:
    """Repeated default lookup requests do not repeat loading or construction."""

    default_module._reset_default_lookup_cache_for_testing()
    table = np.ones((4, 91, 181), dtype=np.uint16)
    names = np.array(["", "ONLY REGION"], dtype="<U16")
    calls = 0

    def fake_load_packaged_assets():
        nonlocal calls
        calls += 1
        return table, names

    monkeypatch.setattr(default_module, "load_packaged_assets", fake_load_packaged_assets)
    first = default_module.get_default_lookup()
    second = default_module.get_default_lookup()
    assert first is second
    assert calls == 1
    default_module._reset_default_lookup_cache_for_testing()


def test_default_lookup_concurrent_first_use_constructs_one_engine(monkeypatch) -> None:
    """Concurrent first callers all receive one single-flight engine instance."""

    default_module._reset_default_lookup_cache_for_testing()
    table = np.ones((4, 91, 181), dtype=np.uint16)
    names = np.array(["", "ONLY REGION"], dtype="<U16")
    calls = 0
    calls_lock = Lock()
    start = Barrier(16)

    def fake_load_packaged_assets():
        nonlocal calls
        with calls_lock:
            calls += 1
        time.sleep(0.02)
        return table, names

    def get_after_barrier():
        start.wait()
        return default_module.get_default_lookup()

    monkeypatch.setattr(default_module, "load_packaged_assets", fake_load_packaged_assets)
    with ThreadPoolExecutor(max_workers=16) as executor:
        engines = list(executor.map(lambda _: get_after_barrier(), range(16)))

    assert calls == 1
    assert len({id(engine) for engine in engines}) == 1
    default_module._reset_default_lookup_cache_for_testing()
