"""ISC FE hierarchy acquisition and independent semantic-pin contracts."""

from __future__ import annotations

import copy
import json
from pathlib import Path

from tools.fetch_isc_fe_regions import fetch_isc_source, parse_isc_html
from tools.isc_fe_source import (
    EXPECTED_SEMANTIC_SHA256,
    normalized_document,
    semantic_sha256,
)


def _synthetic_isc_html() -> bytes:
    """Render the expected semantic hierarchy as simple layout-independent HTML."""

    parts = ["<html><body><h1>Flinn-Engdahl regions</h1>"]
    for region in normalized_document()["seismic_regions"]:
        parts.append(f"<h2>Seismic Region {region['number']}</h2>")
        parts.append(f"<p>{region['name']}</p>")
        for number in region["geographic_regions"]:
            parts.append(f"<div>{number} arbitrary geographical label</div>")
    parts.append("</body></html>")
    return "".join(parts).encode("utf-8")


def test_semantic_pin_is_literal_in_source_module() -> None:
    """Repository code must not restore the self-derived expected-hash defect."""

    source = Path("tools/isc_fe_source.py").read_text(encoding="utf-8")
    assert 'EXPECTED_SEMANTIC_SHA256 = "' in source
    assert "EXPECTED_SEMANTIC_SHA256 = semantic_sha256(normalized_document())" not in source


def test_expected_hierarchy_matches_literal_reviewed_semantic_identity() -> None:
    """The semantic pin is a reviewed literal, not recomputed from hierarchy declarations."""

    assert semantic_sha256(normalized_document()) == EXPECTED_SEMANTIC_SHA256


def test_literal_source_identity_detects_name_or_membership_change() -> None:
    """A hierarchy edit cannot silently update the independently retained digest."""

    changed = copy.deepcopy(normalized_document())
    changed["seismic_regions"][0]["name"] += " changed"
    assert semantic_sha256(changed) != EXPECTED_SEMANTIC_SHA256

    changed = copy.deepcopy(normalized_document())
    changed["seismic_regions"][0]["geographic_regions"].remove(1)
    assert semantic_sha256(changed) != EXPECTED_SEMANTIC_SHA256


def test_parser_reconstructs_expected_semantic_hierarchy() -> None:
    """Visible-layout parsing reproduces the pinned hierarchy under the literal digest."""

    assert parse_isc_html(_synthetic_isc_html()) == normalized_document()


def test_fetch_publishes_verified_normalized_json_without_live_network(tmp_path) -> None:
    """Acquisition verifies current input against literal source identity before publication."""

    output = tmp_path / "fe_regions.json"
    fetch_isc_source(output, fetch_bytes=lambda url: _synthetic_isc_html())
    assert json.loads(output.read_text(encoding="utf-8")) == normalized_document()


def test_runtime_seismic_assets_reproduce_from_verified_normalized_source(tmp_path) -> None:
    """A normalized document matching the literal source pin recreates packaged assets."""

    import numpy as np

    from feregion import get_default_lookup
    from tools.build_assets import build_seismic_assets

    source = tmp_path / "fe_regions.json"
    source.write_text(
        json.dumps(normalized_document(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    crosswalk, names = build_seismic_assets(source)
    engine = get_default_lookup()
    np.testing.assert_array_equal(crosswalk, engine.seismic_by_geographic)
    np.testing.assert_array_equal(names, engine.seismic_names)
