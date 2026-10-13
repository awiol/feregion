"""Validate machine-readable iterative-delivery manifest conformance."""

from __future__ import annotations

import argparse
import json
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

SCHEMA = "feregion-delivery/v1"
PROJECT = "feregion"
REQUIRED_FIELDS = frozenset(
    {
        "schema",
        "project",
        "baseline",
        "target_version",
        "patch_status",
        "artifacts",
        "generation_provenance",
        "review_state",
        "approval_state",
        "verification_state",
        "exclusions",
        "limitations",
    }
)
STATE_FIELDS = ("patch_status", "review_state", "approval_state", "verification_state")
SOURCE_ARTIFACT_ROLES = frozenset(
    {
        "source-recovery-authority",
        "source-archive",
        "source-handoff",
        "source-distribution",
        "built-source-distribution",
    }
)
PATCH_ARTIFACT_ROLES = frozenset({"incremental-replay-evidence", "incremental-patch"})
PATCH_OMISSION_STATES = frozenset(
    {"no-baseline", "not-applicable", "not-generated", "unchanged-source"}
)
_VERSION_RE = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+(?:(?:a|b|rc)[0-9]+)?$")
_STATE_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_GIT_OBJECT_RE = re.compile(r"^[0-9a-f]{40}(?:[0-9a-f]{24})?$")


class DeliveryManifestError(ValueError):
    """Raised when ``delivery.json`` does not satisfy ``REQ-DEL-002``."""


def _non_empty_string(value: object, field: str) -> str:
    """Return one required non-empty string or fail with its field name."""

    if isinstance(value, str) and value.strip():
        return value.strip()
    raise DeliveryManifestError(f"{field} must be a non-empty string")


def _validate_version(value: object, field: str) -> str:
    """Validate the project's release-version syntax used by delivery v1."""

    version = _non_empty_string(value, field)
    if _VERSION_RE.fullmatch(version) is None:
        raise DeliveryManifestError(
            f"{field} must use MAJOR.MINOR.PATCH with an optional aN, bN, or rcN suffix"
        )
    return version


def _validate_sha256(value: object, field: str) -> str:
    """Validate one lowercase hexadecimal SHA-256 identity."""

    digest = _non_empty_string(value, field)
    if _SHA256_RE.fullmatch(digest) is None:
        raise DeliveryManifestError(f"{field} must be a 64-character lowercase SHA-256")
    return digest


def _validate_state(value: object, field: str) -> Mapping[str, Any]:
    """Validate one explicit state record rather than accepting arbitrary prose."""

    if not isinstance(value, Mapping):
        raise DeliveryManifestError(f"{field} must be an object with a state field")
    state = _non_empty_string(value.get("state"), f"{field}.state")
    if _STATE_RE.fullmatch(state) is None:
        raise DeliveryManifestError(f"{field}.state must be a lowercase hyphenated state token")
    return value


def _validate_string_list(value: object, field: str) -> None:
    """Validate an explicit JSON array of non-empty explanatory strings."""

    if not isinstance(value, list):
        raise DeliveryManifestError(f"{field} must be an explicit JSON array")
    for index, item in enumerate(value):
        _non_empty_string(item, f"{field}[{index}]")


def _validate_baseline(value: object) -> None:
    """Require a versioned baseline plus at least one immutable source identity."""

    if not isinstance(value, Mapping) or not value:
        raise DeliveryManifestError("baseline must be a non-empty object")

    version_fields = [name for name in ("version", "declared_version") if name in value]
    if not version_fields:
        raise DeliveryManifestError("baseline must record version or declared_version")
    versions = {_validate_version(value[name], f"baseline.{name}") for name in version_fields}
    if len(versions) != 1:
        raise DeliveryManifestError("baseline version fields must agree")

    identity_count = 0
    for key, item in value.items():
        if key == "sha256" or key.endswith("_sha256"):
            _validate_sha256(item, f"baseline.{key}")
            identity_count += 1
        elif key == "commit" or key.endswith("_commit") or "tree" in key:
            identity = _non_empty_string(item, f"baseline.{key}")
            if _GIT_OBJECT_RE.fullmatch(identity) is None:
                raise DeliveryManifestError(
                    f"baseline.{key} must be a 40- or 64-character lowercase Git object ID"
                )
            identity_count += 1
    if identity_count == 0:
        raise DeliveryManifestError(
            "baseline must record at least one immutable SHA-256, commit, or tree identity"
        )


def _validate_artifacts(value: object, patch_state: str) -> None:
    """Validate artifact identities and required source/patch role coverage."""

    if not isinstance(value, Mapping) or not value:
        raise DeliveryManifestError("artifacts must be a non-empty object")

    roles: set[str] = set()
    for name, record in value.items():
        artifact_name = _non_empty_string(name, "artifacts key")
        if not isinstance(record, Mapping):
            raise DeliveryManifestError(f"artifacts[{artifact_name!r}] must be an object")
        _validate_sha256(record.get("sha256"), f"artifacts[{artifact_name!r}].sha256")
        role = _non_empty_string(record.get("role"), f"artifacts[{artifact_name!r}].role")
        roles.add(role)
        if "bytes" in record:
            size = record["bytes"]
            if isinstance(size, bool) or not isinstance(size, int) or size < 0:
                raise DeliveryManifestError(
                    f"artifacts[{artifact_name!r}].bytes must be a non-negative integer"
                )

    if not roles.intersection(SOURCE_ARTIFACT_ROLES):
        raise DeliveryManifestError(
            "artifacts must include a source archive/handoff with a recognized source role"
        )
    if patch_state not in PATCH_OMISSION_STATES and not roles.intersection(PATCH_ARTIFACT_ROLES):
        raise DeliveryManifestError(
            "patch_status requires an incremental patch/replay artifact with a SHA-256"
        )


def _validate_generation_provenance(value: object) -> None:
    """Validate the minimum generation provenance needed to interpret a delivery."""

    if not isinstance(value, Mapping) or not value:
        raise DeliveryManifestError("generation_provenance must be a non-empty object")
    _non_empty_string(value.get("source"), "generation_provenance.source")
    _non_empty_string(value.get("scope"), "generation_provenance.scope")
    generator_fields = (
        "tool",
        "generator",
        "source_exporter",
        "build_command",
        "candidate_tree",
    )
    if not any(
        isinstance(value.get(field), str) and bool(value[field].strip())
        for field in generator_fields
    ):
        raise DeliveryManifestError(
            "generation_provenance must identify at least one generator, tool, command, or tree"
        )


def validate_delivery_manifest(manifest: Mapping[str, Any]) -> None:
    """Validate the explicit ``feregion-delivery/v1`` contract from ``REQ-DEL-002``."""

    missing = sorted(REQUIRED_FIELDS - manifest.keys())
    if missing:
        raise DeliveryManifestError(
            "delivery manifest is missing required fields: " + ", ".join(missing)
        )
    if manifest["schema"] != SCHEMA:
        raise DeliveryManifestError(f"schema must be {SCHEMA!r}")
    if manifest["project"] != PROJECT:
        raise DeliveryManifestError(f"project must be {PROJECT!r}")

    _validate_baseline(manifest["baseline"])
    _validate_version(manifest["target_version"], "target_version")

    states = {field: _validate_state(manifest[field], field) for field in STATE_FIELDS}
    patch_state = str(states["patch_status"]["state"])
    _validate_artifacts(manifest["artifacts"], patch_state)
    _validate_generation_provenance(manifest["generation_provenance"])
    _validate_string_list(manifest["exclusions"], "exclusions")
    _validate_string_list(manifest["limitations"], "limitations")


def main(argv: list[str] | None = None) -> int:
    """Validate one delivery manifest and fail closed on contract mismatch."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument(
        "--expected-target-version",
        help="fail unless the manifest target_version matches this exact candidate version",
    )
    args = parser.parse_args(argv)
    try:
        payload = json.loads(args.manifest.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise DeliveryManifestError("delivery manifest root must be a JSON object")
        validate_delivery_manifest(payload)
        if (
            args.expected_target_version is not None
            and payload["target_version"] != args.expected_target_version
        ):
            raise DeliveryManifestError(
                "target_version does not match --expected-target-version: "
                f"{payload['target_version']!r} != {args.expected_target_version!r}"
            )
    except (OSError, json.JSONDecodeError, DeliveryManifestError) as exc:
        parser.exit(2, f"error: {exc}\n")
    print(f"valid delivery manifest: {args.manifest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
