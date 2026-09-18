"""Repeatable benchmark population, report, preview, and publication workflow."""

from __future__ import annotations

import argparse
import subprocess
import sys
from collections.abc import Sequence
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
)


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
    """Rebuild the complete native ASV site from all retained result evidence."""

    return _run(["asv", "publish", "--no-pull", "--config", "asv.conf.json"])


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
