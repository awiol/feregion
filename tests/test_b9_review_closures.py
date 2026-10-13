"""Defect-sensitive regressions for the 0.4.0b8 isolated-review closure."""

from __future__ import annotations

import contextlib
import copy
import hashlib
import json
import os
import zipfile
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import BinaryIO

import pytest

from benchmarks import evidence_bundle
from benchmarks.evidence_bundle import EvidenceBundleError
from feregion.geojson import regions_geojson
from tools import delivery_manifest
from tools.delivery_manifest import DeliveryManifestError, validate_delivery_manifest


def _write_project_stub(root: Path, *, version: str = "0.4.0b9") -> None:
    """Create the minimal project metadata needed by evidence-bundle tests."""

    root.mkdir(parents=True, exist_ok=True)
    (root / "pyproject.toml").write_text(
        f'[project]\nname = "feregion"\nversion = "{version}"\n',
        encoding="utf-8",
    )


def _valid_delivery_manifest() -> dict[str, object]:
    """Return one semantically complete ``feregion-delivery/v1`` fixture."""

    return {
        "schema": "feregion-delivery/v1",
        "project": "feregion",
        "baseline": {"version": "0.4.0b8", "sha256": "a" * 64},
        "target_version": "0.4.0b9",
        "patch_status": {"state": "verified-replay"},
        "artifacts": {
            "feregion-v0.4.0b9-handoff.zip": {
                "role": "source-recovery-authority",
                "bytes": 100,
                "sha256": "b" * 64,
            },
            "feregion-v0.4.0b8-to-v0.4.0b9.patch": {
                "role": "incremental-replay-evidence",
                "bytes": 50,
                "sha256": "c" * 64,
            },
        },
        "generation_provenance": {
            "source": "implementation against exact reviewed b8 handoff",
            "scope": "FREG-ISR-001 through FREG-ISR-003 closure",
            "candidate_tree": "d" * 40,
        },
        "review_state": {"state": "self-reviewed-provisional"},
        "approval_state": {"state": "implementation-authorized"},
        "verification_state": {"state": "partial-pass-with-explicit-blocked-gates"},
        "exclusions": ["uv.lock"],
        "limitations": ["hosted CI not observed"],
    }


def _assert_rejected_without_output(
    project_root: Path,
    output: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Require malformed evidence-root topology to fail before any bundle is issued."""

    monkeypatch.setattr(evidence_bundle, "PROJECT_ROOT", project_root)
    with pytest.raises(EvidenceBundleError, match="symbolic-link directory"):
        evidence_bundle.create_bundle(output)
    assert not output.exists()


@pytest.mark.skipif(not hasattr(os, "symlink"), reason="symbolic links unavailable")
def test_evidence_bundle_rejects_symlinked_normalized_evidence_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``dist/benchmarks`` cannot redirect evidence discovery outside the repository."""

    project_root = tmp_path / "repo"
    outside = tmp_path / "outside"
    _write_project_stub(project_root)
    (project_root / "dist").mkdir()
    outside.mkdir()
    (outside / "secret.json").write_text('{"secret": true}\n', encoding="utf-8")
    try:
        (project_root / "dist" / "benchmarks").symlink_to(outside, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"symlink creation unavailable: {exc}")

    _assert_rejected_without_output(project_root, tmp_path / "bundle.zip", monkeypatch)


@pytest.mark.skipif(not hasattr(os, "symlink"), reason="symbolic links unavailable")
def test_evidence_bundle_rejects_symlinked_asv_environment_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The specialized ``.asv/env`` collector uses the common no-follow boundary."""

    project_root = tmp_path / "repo"
    outside = tmp_path / "outside"
    _write_project_stub(project_root)
    (project_root / ".asv").mkdir()
    (outside / "env1").mkdir(parents=True)
    (outside / "env1" / "asv-env-info.json").write_text("{}\n", encoding="utf-8")
    try:
        (project_root / ".asv" / "env").symlink_to(outside, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"symlink creation unavailable: {exc}")

    _assert_rejected_without_output(project_root, tmp_path / "bundle.zip", monkeypatch)


@pytest.mark.skipif(not hasattr(os, "symlink"), reason="symbolic links unavailable")
def test_evidence_bundle_rejects_nested_symlink_parent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A symlink in a parent component cannot bypass leaf-file no-follow checks."""

    project_root = tmp_path / "repo"
    outside = tmp_path / "outside"
    _write_project_stub(project_root)
    (outside / "results" / "host").mkdir(parents=True)
    (outside / "results" / "host" / "secret.json").write_text("{}\n", encoding="utf-8")
    try:
        (project_root / ".asv").symlink_to(outside, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"symlink creation unavailable: {exc}")

    _assert_rejected_without_output(project_root, tmp_path / "bundle.zip", monkeypatch)


def test_delivery_manifest_accepts_semantically_complete_v1_record() -> None:
    """The maintained delivery-v1 fixture remains accepted by semantic validation."""

    validate_delivery_manifest(_valid_delivery_manifest())


@pytest.mark.parametrize(
    ("label", "mutate", "message"),
    (
        (
            "empty baseline",
            lambda manifest: manifest.__setitem__("baseline", {}),
            "baseline",
        ),
        (
            "baseline without immutable identity",
            lambda manifest: manifest.__setitem__("baseline", {"version": "0.4.0b8"}),
            "immutable",
        ),
        (
            "malformed baseline hash",
            lambda manifest: manifest.__setitem__(
                "baseline", {"version": "0.4.0b8", "sha256": "not-a-hash"}
            ),
            "SHA-256",
        ),
        (
            "invalid target version",
            lambda manifest: manifest.__setitem__("target_version", "next-beta"),
            "target_version",
        ),
        (
            "artifact without hash",
            lambda manifest: manifest.__setitem__(
                "artifacts",
                {
                    "source.zip": {
                        "role": "source-recovery-authority",
                    }
                },
            ),
            "sha256",
        ),
        (
            "no source artifact role",
            lambda manifest: manifest.__setitem__(
                "artifacts",
                {
                    "delta.patch": {
                        "role": "incremental-replay-evidence",
                        "sha256": "c" * 64,
                    }
                },
            ),
            "source archive/handoff",
        ),
        (
            "verified patch state without patch artifact",
            lambda manifest: manifest.__setitem__(
                "artifacts",
                {
                    "source.zip": {
                        "role": "source-recovery-authority",
                        "sha256": "b" * 64,
                    }
                },
            ),
            "patch/replay artifact",
        ),
        (
            "weak generation provenance",
            lambda manifest: manifest.__setitem__("generation_provenance", {"source": "x"}),
            "generation_provenance.scope",
        ),
        (
            "string state instead of state record",
            lambda manifest: manifest.__setitem__("review_state", "reviewed"),
            "review_state",
        ),
        (
            "malformed state token",
            lambda manifest: manifest.__setitem__("approval_state", {"state": "APPROVED!"}),
            "state token",
        ),
        (
            "malformed exclusions",
            lambda manifest: manifest.__setitem__("exclusions", ["uv.lock", 42]),
            "exclusions",
        ),
        (
            "malformed limitations",
            lambda manifest: manifest.__setitem__("limitations", [""]),
            "limitations",
        ),
    ),
)
def test_delivery_manifest_rejects_semantically_incomplete_records(
    label: str,
    mutate: Callable[[dict[str, object]], None],
    message: str,
) -> None:
    """Structurally present but semantically invalid delivery evidence must fail closed."""

    manifest = copy.deepcopy(_valid_delivery_manifest())
    mutate(manifest)
    with pytest.raises(DeliveryManifestError, match=message):
        validate_delivery_manifest(manifest)


def test_delivery_manifest_cli_can_bind_expected_target_version(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Release automation can reject a valid manifest for the wrong candidate identity."""

    path = tmp_path / "delivery.json"
    path.write_text(json.dumps(_valid_delivery_manifest()), encoding="utf-8")
    with pytest.raises(SystemExit) as exc_info:
        delivery_manifest.main([str(path), "--expected-target-version", "0.4.0b10"])
    assert exc_info.value.code == 2
    assert "does not match --expected-target-version" in capsys.readouterr().err


def test_evidence_manifest_hashes_exact_archived_stream_under_source_replacement(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Replacement after safe open cannot detach a manifest digest from archived bytes."""

    project_root = tmp_path / "repo"
    _write_project_stub(project_root)
    normalized = project_root / "dist" / "benchmarks"
    normalized.mkdir(parents=True)
    source = normalized / "sample.json"
    before = b'{"state": "before"}\n'
    after = b'{"state": "after"}\n'
    source.write_bytes(before)
    monkeypatch.setattr(evidence_bundle, "PROJECT_ROOT", project_root)

    real_regular_stream = evidence_bundle._regular_stream
    replaced = False

    @contextlib.contextmanager
    def replacing_stream(
        path: Path, *, containment_root: Path | None = None
    ) -> Iterator[tuple[BinaryIO, os.stat_result]]:
        nonlocal replaced
        with real_regular_stream(path, containment_root=containment_root) as opened:
            if path == source and not replaced:
                replacement = source.with_suffix(".replacement")
                replacement.write_bytes(after)
                os.replace(replacement, source)
                replaced = True
            yield opened

    monkeypatch.setattr(evidence_bundle, "_regular_stream", replacing_stream)
    output, manifest = evidence_bundle.create_bundle(tmp_path / "bundle.zip")

    with zipfile.ZipFile(output) as archive:
        archived = archive.read("normalized/sample.json")
        embedded = json.loads(archive.read("benchmark-evidence-manifest.json"))

    record = next(
        item for item in embedded["inventory"] if item["path"] == "normalized/sample.json"
    )
    digest = hashlib.sha256(archived).hexdigest()
    assert replaced is True
    assert source.read_bytes() == after
    assert archived == before
    assert record["size"] == len(archived)
    assert record["sha256"] == digest
    assert manifest["inventory"] == embedded["inventory"]


def test_regions_geojson_documents_missing_seismic_hierarchy_failure() -> None:
    """The constructor documents the hierarchy error already exposed by its writer."""

    documentation = regions_geojson.__doc__ or ""
    assert "SeismicDataUnavailableError" in documentation
