"""Contracts for the bounded 0.5 optimization investigation tooling."""

from __future__ import annotations

from pathlib import Path

from benchmarks import optimization_probe
from benchmarks.campaign import Campaign

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_optimization_probe_separates_public_validation_and_gather_costs() -> None:
    """The probe must expose discriminating stages rather than one aggregate timer."""

    records = optimization_probe.run_size(100, 1, include_pandas=False)
    cases = {record["case"] for record in records}
    assert {
        "geo_to_seismic_public",
        "geo_validation_complete",
        "geo_validation_bounds",
        "geo_validation_name_slot",
        "geo_validation_active_mask",
        "geo_to_seismic_gather",
        "geo_names_public",
        "geo_names_gather",
        "seismic_names_public",
        "seismic_validation_complete",
        "seismic_validation_name_slot",
        "seismic_names_gather",
    } <= cases
    assert all(record["median_ns"] > 0 for record in records)
    assert all(record["operations_per_second"] > 0 for record in records)


def test_optimization_campaign_is_current_revision_diagnostic_only() -> None:
    """The maintained campaign must not become a release gate or history campaign."""

    path = PROJECT_ROOT / "benchmarks/campaigns/optimization-diagnostics.toml"
    campaign = Campaign.from_toml(path)
    assert campaign.campaign_id == "optimization-diagnostics"
    assert campaign.revisions == ("HEAD",)
    assert campaign.load_sizes == (100_000, 1_000_000)
    assert campaign.environment_profile == "release-history"
    assert campaign.record_samples is True
    assert "lookup_geographic_numbers" not in campaign.cases


def test_probe_source_documents_non_release_evidence_boundary() -> None:
    """The mechanism probe must state that its output is diagnostic evidence."""

    text = (PROJECT_ROOT / "benchmarks/optimization_probe.py").read_text(encoding="utf-8")
    assert "not a release-performance gate" in text
