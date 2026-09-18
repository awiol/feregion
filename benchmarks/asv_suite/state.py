"""Retained sidecar state for ASV setup/correctness outcomes."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Literal

BenchmarkState = Literal[
    "correctness_passed",
    "correctness_failed",
    "build_unavailable",
    "execution_failed",
    "not_applicable",
]


def state_path(case_id: str, load_size: int | None) -> Path | None:
    """Return the ASV-run sidecar path, or ``None`` outside an ASV-managed run."""

    conf_dir = os.environ.get("ASV_CONF_DIR")
    commit = os.environ.get("ASV_COMMIT")
    environment = os.environ.get("ASV_ENV_NAME")
    if not conf_dir or not commit or not environment:
        return None
    load = "scalar" if load_size is None else str(load_size)
    return (
        Path(conf_dir) / ".asv" / "feregion-state" / commit / environment / case_id / f"{load}.json"
    )


def record_state(
    case_id: str,
    load_size: int | None,
    state: BenchmarkState,
    *,
    reason: str | None = None,
) -> None:
    """Write one atomic benchmark-state marker when ASV run context is available."""

    path = state_path(case_id, load_size)
    if path is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": 1,
        "case_id": case_id,
        "load_size": load_size,
        "state": state,
        "reason": reason,
        "commit": os.environ.get("ASV_COMMIT"),
        "environment": os.environ.get("ASV_ENV_NAME"),
    }
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)
