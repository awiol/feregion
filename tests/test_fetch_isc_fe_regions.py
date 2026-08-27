"""ISC FE hierarchy acquisition and semantic-normalization contracts."""

from __future__ import annotations

import json

from tools.fetch_isc_fe_regions import fetch_isc_source, parse_isc_html
from tools.isc_fe_source import (
    EXPECTED_SEMANTIC_SHA256,
    normalized_document,
    semantic_sha256,
)


def _synthetic_isc_html() -> bytes:
    """Render the pinned semantic fixture as simple layout-independent HTML."""

    parts = ["<html><body><h1>Flinn-Engdahl regions</h1>"]
    for region in normalized_document()["seismic_regions"]:
        parts.append(f"<h2>Seismic Region {region['number']}</h2>")
        parts.append(f"<p>{region['name']}</p>")
        for number in region["geographic_regions"]:
            parts.append(f"<div>{number} arbitrary geographical label</div>")
    parts.append("</body></html>")
    return "".join(parts).encode("utf-8")


def test_parser_reconstructs_pinned_semantic_hierarchy() -> None:
    """Visible-layout parsing reproduces the normalized source contract exactly."""

    assert parse_isc_html(_synthetic_isc_html()) == normalized_document()


def test_semantic_hash_is_stable_for_pinned_hierarchy() -> None:
    """The source pin protects names and membership rather than HTML formatting."""

    assert semantic_sha256(normalized_document()) == EXPECTED_SEMANTIC_SHA256


def test_fetch_publishes_verified_normalized_json_without_live_network(tmp_path) -> None:
    """Acquisition can be verified deterministically with a controlled source response."""

    output = tmp_path / "fe_regions.json"
    fetch_isc_source(output, fetch_bytes=lambda url: _synthetic_isc_html())
    assert json.loads(output.read_text(encoding="utf-8")) == normalized_document()


def test_runtime_seismic_assets_reproduce_from_normalized_source(tmp_path) -> None:
    """The normalized source deterministically recreates packaged seismic arrays."""

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
