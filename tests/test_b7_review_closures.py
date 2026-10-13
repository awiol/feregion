"""Defect-sensitive regressions for the 0.4.0b6 isolated-review closure."""

from __future__ import annotations

import io
import os
import re
import stat
import subprocess
from pathlib import Path, PurePosixPath
from typing import TextIO

import numpy as np
import pytest

import feregion._resources as resources
import feregion.cli as cli_module
from benchmarks.asv_suite.contracts import STANDARD_LOAD_SIZES
from benchmarks.campaign import (
    Campaign,
    ResolvedRevision,
    benchmark_regex,
    validate_release_revision_pair,
)
from benchmarks.evidence import EvidenceRecord
from benchmarks.evidence_bundle import EvidenceBundleError, _files_under
from benchmarks.regression import compare_release_evidence
from feregion import pandas as pandas_adapter
from feregion.exceptions import DataFileError
from tools._bounded_http import (
    ResponseTooLargeError,
    read_bounded_response,
    read_bounded_response_with_sha256,
)
from tools.delivery_manifest import DeliveryManifestError, validate_delivery_manifest
from tools.export_repository import (
    RepositoryExportError,
    _archive_member_path,
    _safe_identity_component,
    export_repository,
)


def _release_campaign() -> Campaign:
    """Return the smallest valid routine release-comparison campaign."""

    return Campaign(
        campaign_id="release-compare",
        purpose="test release comparison",
        revisions=("baseline", "HEAD"),
        cases=("lookup_geographic_numbers",),
        load_sizes=(10_000, 20_000),
        repetitions=1,
        rounds=1,
        environment_profile="release-history",
        record_samples=True,
    )


def test_release_comparison_rejects_same_resolved_commit() -> None:
    """Different ref spellings cannot make one commit a release comparison."""

    resolved = (
        ResolvedRevision("accepted-prior", "a" * 40),
        ResolvedRevision("HEAD", "a" * 40),
    )
    with pytest.raises(ValueError, match="distinct baseline and candidate commits"):
        validate_release_revision_pair(_release_campaign(), resolved)


def test_non_release_campaign_may_reuse_one_revision() -> None:
    """The distinct-commit invariant remains release-comparison specific."""

    campaign = _release_campaign()
    diagnostic = Campaign(
        campaign_id="diagnostic",
        purpose=campaign.purpose,
        revisions=campaign.revisions,
        cases=campaign.cases,
        load_sizes=campaign.load_sizes,
        repetitions=campaign.repetitions,
        rounds=campaign.rounds,
        environment_profile=campaign.environment_profile,
        record_samples=campaign.record_samples,
    )
    validate_release_revision_pair(
        diagnostic,
        (ResolvedRevision("one", "a" * 40), ResolvedRevision("two", "a" * 40)),
    )


def _evidence(revision: str, load: int, rate: float) -> EvidenceRecord:
    """Return one comparable normalized release-evidence record."""

    return EvidenceRecord(
        case_id="lookup_geographic_numbers",
        case_version=1,
        revision=revision,
        load_size=load,
        result_state="measured",
        correctness_state="passed",
        samples=(0.1,),
        statistic_seconds=0.1,
        operation_count_unit="points",
        operations=load,
        operations_per_second=rate,
        stored_benchmark_version="v",
        machine="host",
        environment="env",
        campaign_id="release-compare",
    )


def test_release_regression_comparator_rejects_same_revision() -> None:
    """Retained evidence cannot bypass the same-revision release gate."""

    records = [_evidence("a" * 40, 10_000, 100.0), _evidence("a" * 40, 20_000, 100.0)]
    decision = compare_release_evidence(records, records, required_loads=(10_000, 20_000))
    assert decision.complete is False
    assert decision.reason == "baseline and candidate evidence identify the same revision"


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("id", "123"),
        ("revisions", '[123, "HEAD"]'),
        ("load_sizes", "[10000.9]"),
        ("repetitions", "3.9"),
        ("rounds", "true"),
        ("record_samples", '"false"'),
    ),
)
def test_campaign_toml_rejects_wrong_but_coercible_types(
    tmp_path: Path, field: str, value: str
) -> None:
    """Campaign parsing rejects the lossy coercions accepted by b6."""

    values = {
        "id": '"typed-test"',
        "revisions": '["base", "HEAD"]',
        "load_sizes": "[10000]",
        "repetitions": "2",
        "rounds": "2",
        "record_samples": "true",
    }
    values[field] = value
    path = tmp_path / "campaign.toml"
    path.write_text(
        "\n".join(
            (
                "[campaign]",
                f"id = {values['id']}",
                'purpose = "typed campaign"',
                f"revisions = {values['revisions']}",
                'cases = ["lookup_geographic_numbers"]',
                f"load_sizes = {values['load_sizes']}",
                f"repetitions = {values['repetitions']}",
                f"rounds = {values['rounds']}",
                'environment_profile = "release-history"',
                f"record_samples = {values['record_samples']}",
            )
        )
        + "\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError):
        Campaign.from_toml(path)


def test_full_grid_selector_does_not_match_prefix_extension() -> None:
    """A scalar singular selector cannot match the plural batch benchmark."""

    campaign = Campaign(
        campaign_id="selector",
        purpose="selector contract",
        revisions=("HEAD",),
        cases=("lookup_geographic_number",),
        load_sizes=STANDARD_LOAD_SIZES,
        repetitions=1,
        rounds=1,
        environment_profile="release-history",
        record_samples=False,
    )
    pattern = benchmark_regex(campaign)
    assert re.search(pattern, "lookup_geographic_number")
    assert not re.search(pattern, "lookup_geographic_numbers(10000)")


@pytest.mark.skipif(not hasattr(os, "symlink"), reason="symbolic links unavailable")
def test_evidence_discovery_rejects_file_symlink(tmp_path: Path) -> None:
    """Evidence discovery cannot dereference an arbitrary file symlink."""

    root = tmp_path / "results"
    root.mkdir()
    outside = tmp_path / "outside.json"
    outside.write_text('{"secret": true}\n', encoding="utf-8")
    try:
        (root / "leak.json").symlink_to(outside)
    except OSError as exc:
        pytest.skip(f"symlink creation unavailable: {exc}")
    with pytest.raises(EvidenceBundleError, match="symbolic links"):
        _files_under(root, "asv/results", "asv-results")


@pytest.mark.skipif(not hasattr(os, "symlink"), reason="symbolic links unavailable")
def test_evidence_discovery_rejects_directory_symlink(tmp_path: Path) -> None:
    """Evidence discovery rejects symlinked directories rather than following them."""

    root = tmp_path / "results"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "secret.json").write_text("{}\n", encoding="utf-8")
    try:
        (root / "linked").symlink_to(outside, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"symlink creation unavailable: {exc}")
    with pytest.raises(EvidenceBundleError, match="symbolic-link directory"):
        _files_under(root, "asv/results", "asv-results")


@pytest.mark.parametrize("value", (".", "..", "a/b", r"a\b", "bad\x01name"))
def test_archive_identity_rejects_unsafe_path_components(tmp_path: Path, value: str) -> None:
    """Project identity metadata cannot become a traversal-capable member root."""

    with pytest.raises(RepositoryExportError, match="path-safe component"):
        _safe_identity_component(value, "project.name", tmp_path / "pyproject.toml")


def test_archive_member_rejects_parent_traversal() -> None:
    """Final member construction independently rejects parent traversal."""

    with pytest.raises(RepositoryExportError, match="unsafe"):
        _archive_member_path(PurePosixPath("feregion"), PurePosixPath("../payload.txt"))


def _git(repo: Path, *arguments: str) -> None:
    """Run one Git command in a disposable exporter repository."""

    subprocess.run(["git", *arguments], cwd=repo, check=True, capture_output=True)


@pytest.mark.skipif(not hasattr(os, "symlink"), reason="symbolic links unavailable")
@pytest.mark.parametrize("broken", (False, True), ids=("valid", "broken"))
def test_exporter_rejects_tracked_symlink_regardless_of_target_state(
    tmp_path: Path, broken: bool
) -> None:
    """A broken tracked symlink cannot be silently treated as a deletion."""

    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    (repo / "pyproject.toml").write_text(
        '[project]\nname = "feregion"\nversion = "0.4.0b7"\n', encoding="utf-8"
    )
    target = repo / "target.txt"
    if not broken:
        target.write_text("target\n", encoding="utf-8")
    try:
        (repo / "link.txt").symlink_to("target.txt")
    except OSError as exc:
        pytest.skip(f"symlink creation unavailable: {exc}")
    _git(repo, "add", "pyproject.toml", "link.txt")
    if not broken:
        _git(repo, "add", "target.txt")
    with pytest.raises(RepositoryExportError, match="symbolic links"):
        export_repository(repo, tmp_path / "handoff.zip")


@pytest.mark.skipif(os.name == "nt", reason="POSIX permission-bit contract")
@pytest.mark.parametrize("mode", (0o600, 0o640, 0o644))
def test_csv_replacement_temp_is_never_more_permissive(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mode: int
) -> None:
    """Replacement sibling permissions are safe before output data is written."""

    destination = tmp_path / "output.csv"
    destination.write_text("old\n", encoding="utf-8")
    os.chmod(destination, mode)
    temporary_paths: list[Path] = []
    observed_modes: list[int] = []
    real_open = cli_module._open_csv_temporary

    def recording_open(path: Path, *, creation_mode: int = 0o666) -> tuple[Path, TextIO]:
        temporary, stream = real_open(path, creation_mode=creation_mode)
        temporary_paths.append(temporary)
        return temporary, stream

    def observe_process(_input: TextIO, output: TextIO, **_kwargs: object) -> None:
        observed_modes.append(stat.S_IMODE(temporary_paths[-1].stat().st_mode))
        output.write("region\n")

    monkeypatch.setattr(cli_module, "_open_csv_temporary", recording_open)
    monkeypatch.setattr(cli_module, "_process_csv", observe_process)
    cli_module._process_csv_to_file(
        io.StringIO("longitude,latitude\n"),
        destination,
        longitude_column="longitude",
        latitude_column="latitude",
        number_column="fe_number",
        include_names=False,
        name_column="fe_region",
        chunk_size=1,
        level="geographic",
    )
    assert observed_modes[0] & ~mode == 0
    assert stat.S_IMODE(destination.stat().st_mode) == mode


@pytest.mark.parametrize("kind", ("empty", "truncated"))
def test_packaged_asset_eof_maps_to_data_file_error_without_cache(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, kind: str
) -> None:
    """Empty/truncated NumPy assets remain inside the package error boundary."""

    original = tuple(array.copy() for array in resources.load_packaged_assets())
    data = tmp_path / "data"
    data.mkdir()
    names = (
        "fe_table.npy",
        "fe_names.npy",
        "fe_seismic_by_geographic.npy",
        "fe_seismic_names.npy",
    )
    for filename, array in zip(names, original, strict=True):
        np.save(data / filename, array, allow_pickle=False)
    if kind == "empty":
        (data / "fe_table.npy").write_bytes(b"")
    else:
        payload = (data / "fe_table.npy").read_bytes()
        (data / "fe_table.npy").write_bytes(payload[:16])

    resources._reset_packaged_assets_cache_for_testing()
    monkeypatch.setattr(resources, "files", lambda _package: tmp_path)
    try:
        with pytest.raises(DataFileError, match="cannot be read"):
            resources.load_packaged_assets()
        assert resources._assets is None
    finally:
        resources._reset_packaged_assets_cache_for_testing()


def test_pandas_docstring_names_value_and_range_failures() -> None:
    """The pandas adapter documents every specified coordinate failure class."""

    documentation = pandas_adapter.lookup_dataframe.__doc__ or ""
    assert "CoordinateValueError" in documentation
    assert "CoordinateRangeError" in documentation


class _Response(io.BytesIO):
    """urllib-like response double with optional length metadata."""

    def __init__(self, payload: bytes, content_length: str | None = None) -> None:
        super().__init__(payload)
        self.headers: dict[str, str] = {}
        if content_length is not None:
            self.headers["Content-Length"] = content_length


def test_bounded_http_rejects_declared_oversize_before_body_read() -> None:
    """An oversized declared length can fail before buffering the body."""

    response = _Response(b"small", content_length="100")
    with pytest.raises(ResponseTooLargeError, match="declares"):
        read_bounded_response(response, max_bytes=10, label="test response")
    assert response.tell() == 0


def test_bounded_http_rejects_actual_oversize_without_content_length() -> None:
    """Missing length metadata cannot bypass the actual byte ceiling."""

    response = _Response(b"x" * 11)
    with pytest.raises(ResponseTooLargeError, match="exceeds"):
        read_bounded_response(response, max_bytes=10, label="test response")
    assert response.tell() == 11


def test_bounded_http_hashes_accepted_bytes_incrementally() -> None:
    """The bounded reader supplies the digest used by pinned source acquisition."""

    import hashlib

    payload = b"pinned-source-bytes"
    data, digest = read_bounded_response_with_sha256(
        _Response(payload), max_bytes=1024, label="test response"
    )
    assert data == payload
    assert digest == hashlib.sha256(payload).hexdigest()


def test_delivery_manifest_requires_explicit_states() -> None:
    """REQ-DEL-002 states cannot be inferred from companion prose."""

    valid = {
        "schema": "feregion-delivery/v1",
        "project": "feregion",
        "baseline": {"version": "0.4.0b6", "sha256": "a" * 64},
        "target_version": "0.4.0b7",
        "patch_status": {"state": "not-applicable"},
        "artifacts": {
            "source.zip": {
                "role": "source-recovery-authority",
                "sha256": "b" * 64,
            }
        },
        "generation_provenance": {
            "source": "test fixture",
            "scope": "delivery-manifest state regression",
            "tool": "delivery-builder",
        },
        "review_state": {"state": "completed"},
        "approval_state": {"state": "not-requested"},
        "verification_state": {"state": "partial"},
        "exclusions": ["uv.lock"],
        "limitations": ["hosted CI not observed"],
    }
    validate_delivery_manifest(valid)
    for missing in (
        "patch_status",
        "generation_provenance",
        "review_state",
        "approval_state",
        "verification_state",
        "exclusions",
    ):
        malformed = dict(valid)
        malformed.pop(missing)
        with pytest.raises(DeliveryManifestError, match=missing):
            validate_delivery_manifest(malformed)


def test_maintained_contracts_do_not_embed_known_candidate_result_phrases() -> None:
    """Candidate observations remain release evidence rather than contract state."""

    paths = (
        Path("docs/feregion-engineering-requirements.md"),
        Path("docs/feregion-design.md"),
        Path("docs/feregion-quality-assurance.md"),
        Path("docs/feregion-verification-traceability.md"),
    )
    forbidden = (
        "reviewed post-b3",
        "corrected b2",
        "fresh b2",
        "real b1",
        "b6 verifies",
        "verified post-b3",
        "127 html files",
        "1,020-file",
    )
    for path in paths:
        text = path.read_text(encoding="utf-8").lower()
        for phrase in forbidden:
            assert phrase not in text, f"{path}: candidate observation remains: {phrase}"
