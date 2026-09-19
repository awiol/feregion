"""Repeatable benchmark population, report, preview, and publication workflow."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_CAMPAIGN_ROOT = _PROJECT_ROOT / "benchmarks" / "campaigns"

# This set covers every maintained benchmark case on HEAD, the supported Python
# matrix, the sparse dependency matrix, and the routine release gate without
# re-running the overlapping NumPy/pandas sensitivity campaign files separately.
_REFRESH_CAMPAIGNS = (
    "smoke.toml",
    "release-compare.toml",
    "head-full.toml",
    "dependency-matrix.toml",
    "python-supported.toml",
    "reference-comparison.toml",
    "diagnostics.toml",
)


def _evidence_snapshot() -> dict[str, object]:
    """Return a content identity for retained evidence used to rebuild a report.

    The digest covers relative paths and bytes from the raw ASV results and project
    state/run/environment sidecars. It intentionally excludes generated HTML.
    """

    roots = (
        _PROJECT_ROOT / ".asv" / "results",
        _PROJECT_ROOT / ".asv" / "feregion-state",
        _PROJECT_ROOT / ".asv" / "feregion-runs",
        _PROJECT_ROOT / ".asv" / "feregion-environments",
    )
    digest = hashlib.sha256()
    count = 0
    for root in roots:
        if not root.is_dir():
            continue
        for path in sorted(item for item in root.rglob("*") if item.is_file()):
            relative = path.relative_to(_PROJECT_ROOT).as_posix().encode("utf-8")
            digest.update(len(relative).to_bytes(8, "big"))
            digest.update(relative)
            data = path.read_bytes()
            digest.update(len(data).to_bytes(8, "big"))
            digest.update(data)
            count += 1
    return {"file_count": count, "sha256": digest.hexdigest()}


def _record_report_rebuild(*, returncode: int, started_at: datetime) -> Path | None:
    """Retain one report-rebuild result when benchmark evidence exists.

    The record proves only the local ASV report-build action and resulting local HTML
    state. External publication remains a separate operation.
    """

    results_dir = _PROJECT_ROOT / ".asv" / "results"
    if not results_dir.is_dir():
        return None
    recorded_at = datetime.now(UTC)
    html_root = _PROJECT_ROOT / ".asv" / "html"
    html_files = (
        [item for item in html_root.rglob("*") if item.is_file()] if html_root.is_dir() else []
    )
    payload = {
        "schema_version": 1,
        "action": "asv-report-rebuild",
        "command": ["asv", "publish", "--no-pull", "--config", "asv.conf.json"],
        "started_at_utc": started_at.isoformat(),
        "recorded_at_utc": recorded_at.isoformat(),
        "returncode": returncode,
        "source_evidence": _evidence_snapshot(),
        "html_index_exists": (html_root / "index.html").is_file(),
        "html_file_count": len(html_files),
    }
    stamp = recorded_at.strftime("%Y%m%dT%H%M%SZ")
    path = _PROJECT_ROOT / ".asv" / "feregion-reports" / f"report-{stamp}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _run(command: Sequence[str]) -> int:
    """Run one workflow command synchronously from the repository root."""

    completed = subprocess.run(list(command), cwd=_PROJECT_ROOT)
    return completed.returncode


def _campaign_command(
    subcommand: str,
    filename: str,
    *,
    repetitions: int | None = None,
    rounds: int | None = None,
    append_samples: bool = False,
) -> list[str]:
    """Build one campaign CLI command with optional measurement overrides."""

    command = [
        sys.executable,
        "-m",
        "benchmarks.campaign",
        subcommand,
        str(_CAMPAIGN_ROOT / filename),
    ]
    if subcommand == "run":
        if repetitions is not None:
            command.extend(["--repetitions", str(repetitions)])
        if rounds is not None:
            command.extend(["--rounds", str(rounds)])
        if append_samples:
            command.append("--append-samples")
    return command


def refresh(
    *,
    repetitions: int | None,
    rounds: int | None,
    append_samples: bool,
    include_history: bool,
) -> int:
    """Populate current-release evidence, evaluate the gate, and rebuild the site."""

    campaigns = list(_REFRESH_CAMPAIGNS)
    if include_history:
        campaigns.append("release-history.toml")
    for filename in campaigns:
        status = _run(_campaign_command("plan", filename))
        if status != 0:
            return status
        status = _run(
            _campaign_command(
                "run",
                filename,
                repetitions=repetitions,
                rounds=rounds,
                append_samples=append_samples,
            )
        )
        if status != 0:
            return status

    check_status = _run(_campaign_command("check", "release-compare.toml"))
    report_status = build_report()
    if report_status != 0:
        return report_status
    return check_status


def build_report() -> int:
    """Rebuild the ASV site and retain a machine-readable local rebuild record."""

    started_at = datetime.now(UTC)
    status = _run(["asv", "publish", "--no-pull", "--config", "asv.conf.json"])
    _record_report_rebuild(returncode=status, started_at=started_at)
    return status


def preview() -> int:
    """Serve the generated ASV site through ASV's local preview server."""

    return _run(["asv", "preview", "--config", "asv.conf.json"])


def stage_publication(*, push: bool) -> int:
    """Update the gh-pages publication branch and optionally push it explicitly."""

    command = ["asv", "gh-pages", "--config", "asv.conf.json"]
    if not push:
        command.insert(2, "--no-push")
    return _run(command)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    refresh_parser = subparsers.add_parser("refresh")
    refresh_parser.add_argument("--repetitions", type=int)
    refresh_parser.add_argument("--rounds", type=int)
    refresh_parser.add_argument(
        "--append-samples",
        action="store_true",
        help="append new raw samples to existing ASV results instead of replacing them",
    )
    refresh_parser.add_argument(
        "--history",
        action="store_true",
        help="also rerun the maintained backward-compatible release-history campaign",
    )
    subparsers.add_parser("report")
    subparsers.add_parser("preview")
    publish_parser = subparsers.add_parser("publish")
    publish_parser.add_argument(
        "--push",
        action="store_true",
        help="allow ASV to push the updated gh-pages branch to origin",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the selected release benchmark workflow action."""

    args = _parser().parse_args(argv)
    if args.command == "refresh":
        if args.repetitions is not None and args.repetitions < 1:
            raise SystemExit("--repetitions must be at least 1")
        if args.rounds is not None and args.rounds < 1:
            raise SystemExit("--rounds must be at least 1")
        return refresh(
            repetitions=args.repetitions,
            rounds=args.rounds,
            append_samples=args.append_samples,
            include_history=args.history,
        )
    if args.command == "report":
        return build_report()
    if args.command == "preview":
        return preview()
    return stage_publication(push=args.push)


if __name__ == "__main__":
    sys.exit(main())
