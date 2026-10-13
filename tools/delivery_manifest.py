"""Validate machine-readable iterative-delivery manifest conformance."""

from __future__ import annotations

import argparse
import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

REQUIRED_FIELDS = frozenset(
    {
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


class DeliveryManifestError(ValueError):
    """Raised when ``delivery.json`` does not satisfy ``REQ-DEL-002``."""


def _validate_state(value: object, field: str) -> None:
    if isinstance(value, str) and value.strip():
        return
    if (
        isinstance(value, Mapping)
        and isinstance(value.get("state"), str)
        and value["state"].strip()
    ):
        return
    raise DeliveryManifestError(f"{field} must record an explicit non-empty state")


def validate_delivery_manifest(manifest: Mapping[str, Any]) -> None:
    """Validate explicit state/provenance categories required by ``REQ-DEL-002``."""

    missing = sorted(REQUIRED_FIELDS - manifest.keys())
    if missing:
        raise DeliveryManifestError(
            "delivery manifest is missing required fields: " + ", ".join(missing)
        )
    if not isinstance(manifest["target_version"], str) or not manifest["target_version"].strip():
        raise DeliveryManifestError("target_version must be a non-empty string")
    for field in STATE_FIELDS:
        _validate_state(manifest[field], field)
    if not isinstance(manifest["baseline"], (str, Mapping)):
        raise DeliveryManifestError("baseline must explicitly identify the delivery baseline")
    if not isinstance(manifest["artifacts"], Mapping) or not manifest["artifacts"]:
        raise DeliveryManifestError("artifacts must record source/archive hash identities")
    if (
        not isinstance(manifest["generation_provenance"], Mapping)
        or not manifest["generation_provenance"]
    ):
        raise DeliveryManifestError("generation_provenance must be a non-empty object")
    for field in ("exclusions", "limitations"):
        value = manifest[field]
        if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
            raise DeliveryManifestError(f"{field} must be an explicit array, possibly empty")


def main(argv: list[str] | None = None) -> int:
    """Validate one delivery manifest and fail closed on contract mismatch."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    args = parser.parse_args(argv)
    try:
        payload = json.loads(args.manifest.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise DeliveryManifestError("delivery manifest root must be a JSON object")
        validate_delivery_manifest(payload)
    except (OSError, json.JSONDecodeError, DeliveryManifestError) as exc:
        parser.exit(2, f"error: {exc}\n")
    print(f"valid delivery manifest: {args.manifest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
