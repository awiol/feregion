"""Project-owned helpers for extending the ASV static benchmark report.

This module does not replace ASV's graph generation, result history, regression
analysis, or static-site generator.  It adds a small project summary page after
ASV has generated its normal site.  Keeping the transformation here makes the
ASV-version-specific boundary explicit and testable.
"""

from __future__ import annotations

import json
import shutil
from collections.abc import Mapping
from pathlib import Path
from typing import Any

ASV_REPORT_ASSET_DIR = Path(__file__).with_name("report_assets")
_REPORT_MARKER = "<!-- feregion-report-extension -->"


def _json_count(path: Path, key: str) -> int:
    """Return the length of one JSON list field, or zero when unavailable."""

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return 0
    value = payload.get(key, []) if isinstance(payload, dict) else []
    return len(value) if isinstance(value, list) else 0


def _serializable_params(graphs: Any) -> dict[str, list[Any]]:
    """Return deterministic graph-environment parameter values for the summary."""

    try:
        params = graphs.get_params()
    except AttributeError:
        return {}
    result: dict[str, list[Any]] = {}
    for key, values in params.items():
        result[str(key)] = sorted(values, key=lambda value: "" if value is None else str(value))
    return result


def build_publisher_payload(
    *,
    html_dir: Path,
    benchmarks: Mapping[str, Mapping[str, Any]],
    graphs: Any,
    revisions: Mapping[str, int],
    repo: Any,
) -> dict[str, Any]:
    """Build the project summary payload from ASV publisher inputs.

    The payload intentionally contains only information already available to
    ASV at publish time.  Project-specific release-gate evidence remains in the
    separate normalized evidence files produced by ``campaign check``.
    """

    tags_by_commit: dict[str, list[str]] = {}
    try:
        tags = repo.get_tags()
    except AttributeError:
        tags = {}
    for tag, commit in tags.items():
        if commit in revisions:
            tags_by_commit.setdefault(commit, []).append(str(tag))
    for values in tags_by_commit.values():
        values.sort()

    rows: list[dict[str, Any]] = []
    for name, benchmark in sorted(benchmarks.items()):
        param_names = [str(value) for value in benchmark.get("param_names", [])]
        rows.append(
            {
                "name": name,
                "pretty_name": benchmark.get("pretty_name") or name,
                "pretty_source": benchmark.get("pretty_source") or benchmark.get("code") or "",
                "parameterized": bool(benchmark.get("params")),
                "param_names": param_names,
                "scaling_href": (
                    f"#{name}?x-axis=size&y-axis-scale=log" if "size" in param_names else f"#{name}"
                ),
            }
        )

    revision_rows = [
        {
            "commit": commit,
            "revision": int(revision),
            "tags": tags_by_commit.get(commit, []),
        }
        for commit, revision in sorted(revisions.items(), key=lambda item: item[1])
    ]
    return {
        "schema_version": 1,
        "benchmark_count": len(rows),
        "revision_count": len(revision_rows),
        "regression_count": _json_count(html_dir / "regressions.json", "regressions"),
        "environment_parameters": _serializable_params(graphs),
        "revisions": revision_rows,
        "benchmarks": rows,
        "asv_regression_note": (
            "ASV regressions are sensitive investigation signals. The feregion release gate "
            "is separate: review is triggered only by >25% slowdown at two adjacent maintained "
            "load sizes of at least 10,000 under one comparable machine/environment basis."
        ),
        "migration_authority_note": (
            "Reviewed post-b3 evidence satisfies REQ-PERF-017. ASV plus the project-owned "
            "campaign/evidence/regression layers are the primary benchmark-evidence path for "
            "0.4; predecessor benchmark tooling remains runnable for compatibility, "
            "investigation, and historical provenance."
        ),
        "throughput_note": (
            "Normalized feregion evidence retains declared operations and operations-per-second. "
            "The project release threshold is evaluated in throughput space even though native "
            "ASV graphs normally display elapsed time."
        ),
    }


def install_report_extension(html_dir: Path) -> None:
    """Install additive feregion page assets into one freshly published ASV site.

    ASV 0.6.x recreates ``html_dir`` from its packaged frontend on every
    ``publish``.  The project therefore reapplies this bounded extension after
    each publish instead of modifying ASV's installed package or maintaining a
    fork of its frontend.
    """

    html_dir = html_dir.resolve()
    index_path = html_dir / "index.html"
    text = index_path.read_text(encoding="utf-8")
    if _REPORT_MARKER not in text:
        script = (
            f"    {_REPORT_MARKER}\n"
            '    <script language="javascript" type="text/javascript" '
            'src="feregion-report.js"></script>\n'
            '    <link href="feregion-report.css" rel="stylesheet" type="text/css"/>\n'
        )
        if "  </head>" not in text:
            raise ValueError("unsupported ASV index template: missing </head> insertion point")
        text = text.replace("  </head>", script + "  </head>", 1)

        nav = '        <li id="nav-li-feregion"><a href="#/feregion">feregion summary</a></li>\n'
        anchor = '\t<li id="nav-li-regressions"><a href="#/regressions">Regressions</a></li>\n'
        if anchor not in text:
            raise ValueError("unsupported ASV index template: missing regressions navigation")
        text = text.replace(anchor, anchor + nav, 1)

        display = (
            '    <div id="feregion-display" style="display: none; position: absolute; '
            'left: 0; top: 55px; right: 0; bottom: 0; overflow-y: auto;">\n'
            '      <div id="feregion-body" class="container-fluid"></div>\n'
            "    </div>\n"
        )
        display_anchor = '    <div id="regressions-display"'
        if display_anchor not in text:
            raise ValueError("unsupported ASV index template: missing regressions display")
        text = text.replace(display_anchor, display + display_anchor, 1)
        index_path.write_text(text, encoding="utf-8")

    for name in ("feregion-report.js", "feregion-report.css"):
        shutil.copyfile(ASV_REPORT_ASSET_DIR / name, html_dir / name)
