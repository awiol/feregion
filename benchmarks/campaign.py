"""Thin campaign planner and ASV command adapter for feregion benchmarks."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
import tomllib
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .asv_suite.contracts import CASES, STANDARD_LOAD_SIZES

PROFILE_CONFIG: dict[str, dict[str, Any]] = {
    "release-history": {
        "pythons": ["3.12"],
        "matrix": {"req": {"numpy": ["1.26.4"], "pandas": ["2.1.4"]}},
    },
    "python-supported": {
        "pythons": ["3.11", "3.12", "3.13", "3.14"],
        "matrix": {"req": {"numpy": ["2.3.5"], "pandas": ["2.3.3"]}},
    },
    "numpy-sensitivity": {
        "pythons": ["3.12"],
        "matrix": {
            "req": {
                "numpy": ["1.26.4", "2.0.2", "2.2.6", "2.5.2"],
                "pandas": ["2.1.4"],
            }
        },
    },
    "pandas-sensitivity": {
        "pythons": ["3.12"],
        "matrix": {
            "req": {
                "numpy": ["1.26.4"],
                "pandas": ["2.1.4", "2.2.3", "2.3.3", "3.0.5"],
            }
        },
    },
}

ASV_BUILD_COMMAND = [
    "python -m pip wheel --no-deps -w {build_cache_dir} {build_dir}",
]
ASV_INSTALL_COMMAND = [
    "in-dir={env_dir} python -m pip install --no-deps --force-reinstall {wheel_file}",
]

_REVISION_META_CHARS = re.compile(r"(?:\.\.|@\{|[\s~^:?*\[\\])")
_HEX_COMMIT = re.compile(r"^[0-9A-Fa-f]{7,40}$")


@dataclass(frozen=True, slots=True)
class ResolvedRevision:
    """One operator revision identity resolved to one immutable Git commit."""

    requested: str
    commit: str

    @property
    def asv_run_selector(self) -> str:
        """Return Git syntax that selects exactly this commit for ``asv run``."""

        return f"{self.commit}^!"


def _validate_revision_identity(revision: str) -> None:
    """Reject Git range/expression syntax from campaign revision identities."""

    if not revision:
        raise ValueError("campaign revision identity must not be empty")
    if revision.startswith("-") or _REVISION_META_CHARS.search(revision):
        raise ValueError(
            f"campaign revision must be one ref/commit identity, not Git range syntax: {revision!r}"
        )
    if revision == "HEAD" or _HEX_COMMIT.fullmatch(revision):
        return
    # Git ref names cannot contain these expression characters. Remaining names
    # are allowed here and are authoritatively resolved by ``git rev-parse``.


def resolve_revision(revision: str, *, repository: Path) -> ResolvedRevision:
    """Resolve one campaign revision to an immutable commit or fail preflight."""

    _validate_revision_identity(revision)
    completed = subprocess.run(
        ["git", "rev-parse", "--verify", f"{revision}^{{commit}}"],
        cwd=repository.resolve(),
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        detail = completed.stderr.strip() or "revision did not resolve to a commit"
        raise ValueError(f"cannot resolve campaign revision {revision!r}: {detail}")
    commit = completed.stdout.strip()
    if not re.fullmatch(r"[0-9A-Fa-f]{40}", commit):
        raise ValueError(f"Git returned an unexpected commit identity for {revision!r}: {commit!r}")
    return ResolvedRevision(revision, commit.lower())


def resolve_revisions(campaign: Campaign, *, repository: Path) -> tuple[ResolvedRevision, ...]:
    """Resolve all selected campaign revisions before invoking ASV."""

    return tuple(
        resolve_revision(revision, repository=repository) for revision in campaign.revisions
    )


@dataclass(frozen=True, slots=True)
class Campaign:
    """Resolved operator intent for one benchmark campaign."""

    campaign_id: str
    purpose: str
    revisions: tuple[str, ...]
    cases: tuple[str, ...]
    load_sizes: tuple[int, ...]
    repetitions: int
    rounds: int
    environment_profile: str
    record_samples: bool

    @classmethod
    def from_toml(cls, path: Path) -> Campaign:
        """Load and validate a campaign TOML file."""

        with path.open("rb") as handle:
            data = tomllib.load(handle)
        config = data.get("campaign", data)
        campaign = cls(
            campaign_id=str(config["id"]),
            purpose=str(config.get("purpose", "benchmark campaign")),
            revisions=tuple(str(value) for value in config["revisions"]),
            cases=tuple(str(value) for value in config.get("cases", CASES)),
            load_sizes=tuple(int(value) for value in config.get("load_sizes", STANDARD_LOAD_SIZES)),
            repetitions=int(config.get("repetitions", 5)),
            rounds=int(config.get("rounds", 3)),
            environment_profile=str(config.get("environment_profile", "release-history")),
            record_samples=bool(config.get("record_samples", True)),
        )
        campaign.validate()
        return campaign

    def validate(self) -> None:
        """Reject campaign values that cannot map to the maintained contract."""

        if not self.revisions:
            raise ValueError("campaign must select at least one revision")
        if not self.cases:
            raise ValueError("campaign must select at least one benchmark case")
        if not self.load_sizes:
            raise ValueError("campaign must select at least one load size")
        unknown = sorted(set(self.cases) - CASES.keys())
        if unknown:
            raise ValueError(f"unknown benchmark cases: {', '.join(unknown)}")
        invalid_sizes = sorted(set(self.load_sizes) - set(STANDARD_LOAD_SIZES))
        if invalid_sizes:
            raise ValueError(f"unsupported load sizes: {invalid_sizes}")
        if self.repetitions < 1 or self.rounds < 1:
            raise ValueError("repetitions and rounds must be positive integers")
        if self.environment_profile not in PROFILE_CONFIG:
            raise ValueError(f"unknown environment profile: {self.environment_profile}")

    def plan(
        self,
        *,
        repository: Path,
        resolved_revisions: Sequence[ResolvedRevision] | None = None,
    ) -> dict[str, Any]:
        """Return an inspectable plan with immutable revision identities."""

        resolved = (
            tuple(resolved_revisions)
            if resolved_revisions is not None
            else resolve_revisions(self, repository=repository)
        )
        result = asdict(self)
        result["profile"] = PROFILE_CONFIG[self.environment_profile]
        result["case_versions"] = {case: CASES[case].case_version for case in self.cases}
        result["resolved_revisions"] = [asdict(item) for item in resolved]
        return result


def build_asv_config(
    campaign: Campaign,
    *,
    repository: Path,
    resolved_revisions: Sequence[ResolvedRevision] | None = None,
) -> dict[str, Any]:
    """Build the bounded ASV configuration for one campaign."""

    profile = PROFILE_CONFIG[campaign.environment_profile]
    branches = (
        [item.commit for item in resolved_revisions]
        if resolved_revisions is not None
        else list(campaign.revisions)
    )
    return {
        "version": 1,
        "project": "feregion",
        "repo": str(repository.resolve()),
        "branches": branches,
        "environment_type": "uv",
        "pythons": profile["pythons"],
        "matrix": profile["matrix"],
        "benchmark_dir": "benchmarks/asv_suite",
        "env_dir": ".asv/env",
        "results_dir": ".asv/results",
        "html_dir": ".asv/html",
        "build_command": list(ASV_BUILD_COMMAND),
        "install_command": list(ASV_INSTALL_COMMAND),
    }


def benchmark_regex(campaign: Campaign) -> str:
    """Return an ASV regex selecting the requested semantic cases and load parameters."""

    escaped_cases = [re.escape(case) for case in campaign.cases]
    if set(campaign.load_sizes) == set(STANDARD_LOAD_SIZES):
        return "|".join(escaped_cases)

    scalar_cases = [
        re.escape(case) for case in campaign.cases if not CASES[case].load_parameterized
    ]
    load_cases = [re.escape(case) for case in campaign.cases if CASES[case].load_parameterized]
    expressions: list[str] = []
    if scalar_cases:
        expressions.append(rf"(?:{'|'.join(scalar_cases)})$")
    if load_cases:
        size_expr = "|".join(re.escape(str(size)) for size in campaign.load_sizes)
        expressions.append(rf"(?:{'|'.join(load_cases)})\((?:{size_expr})\)$")
    return "|".join(expressions)


def _run_asv(
    campaign: Campaign,
    command: Sequence[str],
    *,
    repository: Path,
    resolved_revisions: Sequence[ResolvedRevision] | None = None,
) -> int:
    """Run one ASV subcommand with a temporary config rooted at the repository."""

    if not command:
        raise ValueError("ASV command must contain a subcommand")

    repository = repository.resolve()
    config = build_asv_config(
        campaign, repository=repository, resolved_revisions=resolved_revisions
    )
    with tempfile.NamedTemporaryFile(
        "w",
        prefix=".asv-campaign-",
        suffix=".json",
        dir=repository,
        delete=False,
        encoding="utf-8",
    ) as handle:
        json.dump(config, handle, indent=2)
        config_path = Path(handle.name)
    try:
        completed = subprocess.run(
            ["asv", *command, "--config", str(config_path)],
            cwd=repository,
        )
        return completed.returncode
    finally:
        config_path.unlink(missing_ok=True)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    for name in ("plan", "run", "compare", "report"):
        item = subparsers.add_parser(name)
        item.add_argument("config", type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the campaign operator CLI."""

    args = _parser().parse_args(argv)
    campaign = Campaign.from_toml(args.config)
    repository = Path(__file__).resolve().parents[1]
    try:
        resolved_revisions = resolve_revisions(campaign, repository=repository)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    if args.command == "plan":
        print(
            json.dumps(
                campaign.plan(repository=repository, resolved_revisions=resolved_revisions),
                indent=2,
                sort_keys=True,
            )
        )
        return 0
    if args.command == "run":
        for revision in resolved_revisions:
            command: list[str] = [
                "run",
                revision.asv_run_selector,
                "--bench",
                benchmark_regex(campaign),
            ]
            command.extend(["--attribute", f"repeat={campaign.repetitions}"])
            command.extend(["--attribute", f"rounds={campaign.rounds}"])
            if campaign.record_samples:
                command.append("--record-samples")
            status = _run_asv(
                campaign,
                command,
                repository=repository,
                resolved_revisions=resolved_revisions,
            )
            if status != 0:
                return status
        return 0
    if args.command == "compare":
        if len(resolved_revisions) != 2:
            raise SystemExit("compare requires exactly two campaign revisions")
        return _run_asv(
            campaign,
            ["compare", resolved_revisions[0].commit, resolved_revisions[1].commit],
            repository=repository,
            resolved_revisions=resolved_revisions,
        )
    return _run_asv(
        campaign,
        ["publish"],
        repository=repository,
        resolved_revisions=resolved_revisions,
    )


if __name__ == "__main__":
    sys.exit(main())
