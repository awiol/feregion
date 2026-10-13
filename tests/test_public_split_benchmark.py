"""Contract tests for the retained 0.6 public split benchmark procedure."""

from __future__ import annotations

from benchmarks import public_split_benchmark


def test_public_split_benchmark_retains_reproducible_protocol_and_samples() -> None:
    """A small run records the exact procedure and one sample per repetition/operation."""

    report = public_split_benchmark.run_benchmark(sizes=(128,), repetitions=3)

    assert report["schema"] == "feregion-public-split-direct-v2"
    assert report["protocol"]["seed"] == public_split_benchmark.SEED
    assert report["protocol"]["sizes"] == [128]
    assert report["protocol"]["repetitions"] == 3
    assert report["protocol"]["warmup_calls_per_operation"] == 1
    assert report["protocol"]["alternation"].startswith("forward on even")

    row = report["rows"][0]
    assert row["points"] == 128
    for operation in report["protocol"]["operation_order"]:
        assert len(row["samples_seconds"][operation]) == 3
        assert row["median_seconds"][operation] > 0
    assert row["ratios"]["geographic_matrix_over_split"] > 0
    assert row["ratios"]["geographic_stack_over_split"] > 0
    assert row["ratios"]["seismic_matrix_over_split"] > 0
