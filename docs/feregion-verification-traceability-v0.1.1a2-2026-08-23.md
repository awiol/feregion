# feregion verification traceability

| Field | Value |
|---|---|
| Document version | `0.1.1a2` |
| Implementation target | `0.1.1a2` |
| Document date | `2026-08-23` |
| Status | Current alpha traceability |

## Purpose

This document maps each current requirement identifier to its primary verification evidence. A mapping identifies where evidence is expected; it does not claim that every environment-dependent check has run locally. Delivery verification records state the observed result and limitation for each release.

## Requirement-to-evidence map

| Requirement | Primary verification evidence |
|---|---|
| `REQ-FE-001` | `tests/test_core_scalar.py`, `tests/test_core_array_positive.py`, source-reproduction differential tests |
| `REQ-FE-002` | `tests/test_core_scalar.py`, `tests/test_core_array_positive.py`, source-reproduction differential tests |
| `REQ-FE-003` | `tests/test_core_scalar.py`, `tests/test_core_array_positive.py`, source-reproduction differential tests |
| `REQ-FE-004` | `tests/test_core_scalar.py`, `tests/test_core_array_positive.py`, source-reproduction differential tests |
| `REQ-API-001` | `tests/test_public_api.py`, `tests/test_region.py`, `tests/test_engine_data_invariants.py` |
| `REQ-API-002` | `tests/test_public_api.py`, `tests/test_region.py`, `tests/test_engine_data_invariants.py` |
| `REQ-API-003` | `tests/test_public_api.py`, `tests/test_region.py`, `tests/test_engine_data_invariants.py` |
| `REQ-API-004` | `tests/test_public_api.py`, `tests/test_region.py`, `tests/test_engine_data_invariants.py` |
| `REQ-API-005` | `tests/test_public_api.py`, `tests/test_region.py`, `tests/test_engine_data_invariants.py` |
| `REQ-API-006` | `tests/test_public_api.py`, `tests/test_region.py`, `tests/test_engine_data_invariants.py` |
| `REQ-NP-001` | core array tests; `tests/test_engine_data_invariants.py`; benchmark evidence for hot-path constraints |
| `REQ-NP-002` | core array tests; `tests/test_engine_data_invariants.py`; benchmark evidence for hot-path constraints |
| `REQ-NP-003` | core array tests; `tests/test_engine_data_invariants.py`; benchmark evidence for hot-path constraints |
| `REQ-NP-004` | core array tests; `tests/test_engine_data_invariants.py`; benchmark evidence for hot-path constraints |
| `REQ-NP-006` | core array tests; `tests/test_engine_data_invariants.py`; benchmark evidence for hot-path constraints |
| `REQ-NP-007` | core array tests; `tests/test_engine_data_invariants.py`; benchmark evidence for hot-path constraints |
| `REQ-PD-001` | `tests/test_pandas.py` |
| `REQ-PD-002` | `tests/test_pandas.py` |
| `REQ-PD-003` | `tests/test_pandas.py` |
| `REQ-PD-004` | `tests/test_pandas.py` |
| `REQ-PD-005` | `tests/test_pandas.py` |
| `REQ-PD-006` | `tests/test_pandas.py` |
| `REQ-ERR-001` | invalid-input core tests, `tests/test_pandas.py`, exact-exception helpers |
| `REQ-ERR-002` | invalid-input core tests, `tests/test_pandas.py`, exact-exception helpers |
| `REQ-ERR-003` | invalid-input core tests, `tests/test_pandas.py`, exact-exception helpers |
| `REQ-ERR-004` | invalid-input core tests, `tests/test_pandas.py`, exact-exception helpers |
| `REQ-ERR-005` | invalid-input core tests, `tests/test_pandas.py`, exact-exception helpers |
| `REQ-ERR-006` | invalid-input core tests, `tests/test_pandas.py`, exact-exception helpers |
| `REQ-CLI-001` | `tests/test_cli.py` |
| `REQ-CLI-002` | `tests/test_cli.py` |
| `REQ-CLI-003` | `tests/test_cli.py` |
| `REQ-CLI-004` | `tests/test_cli.py` |
| `REQ-CLI-005` | `tests/test_cli.py` |
| `REQ-CLI-006` | `tests/test_cli.py` |
| `REQ-CLI-007` | `tests/test_cli.py` |
| `REQ-CLI-008` | `tests/test_cli.py` |
| `REQ-CLI-009` | `tests/test_cli.py` |
| `REQ-CLI-010` | `tests/test_cli.py` |
| `REQ-CLI-011` | `tests/test_cli.py` |
| `REQ-GEO-001` | `tests/test_geojson.py` |
| `REQ-GEO-002` | `tests/test_geojson.py` |
| `REQ-GEO-003` | `tests/test_geojson.py` |
| `REQ-GEO-004` | `tests/test_geojson.py` |
| `REQ-GEO-005` | `tests/test_geojson.py` |
| `REQ-DATA-001` | `tests/test_packaged_assets.py`, `tests/test_resources_failures.py`, `tests/test_default_cache.py`, `tests/test_fetch_obspy_fe_data.py`, `tests/test_source_reproduction.py` |
| `REQ-DATA-002` | `tests/test_packaged_assets.py`, `tests/test_resources_failures.py`, `tests/test_default_cache.py`, `tests/test_fetch_obspy_fe_data.py`, `tests/test_source_reproduction.py` |
| `REQ-DATA-003` | `tests/test_packaged_assets.py`, `tests/test_resources_failures.py`, `tests/test_default_cache.py`, `tests/test_fetch_obspy_fe_data.py`, `tests/test_source_reproduction.py` |
| `REQ-DATA-004` | `tests/test_packaged_assets.py`, `tests/test_resources_failures.py`, `tests/test_default_cache.py`, `tests/test_fetch_obspy_fe_data.py`, `tests/test_source_reproduction.py` |
| `REQ-DATA-005` | `tests/test_packaged_assets.py`, `tests/test_resources_failures.py`, `tests/test_default_cache.py`, `tests/test_fetch_obspy_fe_data.py`, `tests/test_source_reproduction.py` |
| `REQ-DATA-006` | `tests/test_packaged_assets.py`, `tests/test_resources_failures.py`, `tests/test_default_cache.py`, `tests/test_fetch_obspy_fe_data.py`, `tests/test_source_reproduction.py` |
| `REQ-DATA-007` | `tests/test_packaged_assets.py`, `tests/test_resources_failures.py`, `tests/test_default_cache.py`, `tests/test_fetch_obspy_fe_data.py`, `tests/test_source_reproduction.py` |
| `REQ-DATA-008` | `tests/test_packaged_assets.py`, `tests/test_resources_failures.py`, `tests/test_default_cache.py`, `tests/test_fetch_obspy_fe_data.py`, `tests/test_source_reproduction.py` |
| `REQ-DATA-009` | `tests/test_packaged_assets.py`, `tests/test_resources_failures.py`, `tests/test_default_cache.py`, `tests/test_fetch_obspy_fe_data.py`, `tests/test_source_reproduction.py` |
| `REQ-DATA-010` | `tests/test_packaged_assets.py`, `tests/test_resources_failures.py`, `tests/test_default_cache.py`, `tests/test_fetch_obspy_fe_data.py`, `tests/test_source_reproduction.py` |
| `REQ-DATA-011` | `tests/test_packaged_assets.py`, `tests/test_resources_failures.py`, `tests/test_default_cache.py`, `tests/test_fetch_obspy_fe_data.py`, `tests/test_source_reproduction.py` |
| `REQ-NP-005` | core array tests; `tests/test_engine_data_invariants.py`; benchmark evidence for hot-path constraints |
| `REQ-TEST-001` | pytest suite plus CI matrix in `.github/workflows/ci.yml` |
| `REQ-TEST-002` | pytest suite plus CI matrix in `.github/workflows/ci.yml` |
| `REQ-TEST-003` | pytest suite plus CI matrix in `.github/workflows/ci.yml` |
| `REQ-TEST-004` | pytest suite plus CI matrix in `.github/workflows/ci.yml` |
| `REQ-TEST-005` | pytest suite plus CI matrix in `.github/workflows/ci.yml` |
| `REQ-TEST-006` | pytest suite plus CI matrix in `.github/workflows/ci.yml` |
| `REQ-TEST-007` | pytest suite plus CI matrix in `.github/workflows/ci.yml` |
| `REQ-TEST-008` | pytest suite plus CI matrix in `.github/workflows/ci.yml` |
| `REQ-TEST-009` | pytest suite plus CI matrix in `.github/workflows/ci.yml` |
| `REQ-TEST-010` | pytest suite plus CI matrix in `.github/workflows/ci.yml` |
| `REQ-TEST-011` | pytest suite plus CI matrix in `.github/workflows/ci.yml` |
| `REQ-TEST-012` | pytest suite plus CI matrix in `.github/workflows/ci.yml` |
| `REQ-TEST-013` | pytest suite plus CI matrix in `.github/workflows/ci.yml` |
| `REQ-PERF-001` | `benchmarks/run_benchmark.py`, `benchmarks/test_lookup_benchmark.py`, delivery-side benchmark report |
| `REQ-PERF-002` | `benchmarks/run_benchmark.py`, `benchmarks/test_lookup_benchmark.py`, delivery-side benchmark report |
| `REQ-PERF-003` | `benchmarks/run_benchmark.py`, `benchmarks/test_lookup_benchmark.py`, delivery-side benchmark report |
| `REQ-PERF-004` | `benchmarks/run_benchmark.py`, `benchmarks/test_lookup_benchmark.py`, delivery-side benchmark report |
| `REQ-PKG-001` | `tests/test_project_metadata.py`, `.github/workflows/ci.yml`, `tools/verify_wheel.py`, distribution-build verification |
| `REQ-PKG-002` | `tests/test_project_metadata.py`, `.github/workflows/ci.yml`, `tools/verify_wheel.py`, distribution-build verification |
| `REQ-PKG-003` | `tests/test_project_metadata.py`, `.github/workflows/ci.yml`, `tools/verify_wheel.py`, distribution-build verification |
| `REQ-PKG-004` | `tests/test_project_metadata.py`, `.github/workflows/ci.yml`, `tools/verify_wheel.py`, distribution-build verification |
| `REQ-PKG-005` | `tests/test_project_metadata.py`, `.github/workflows/ci.yml`, `tools/verify_wheel.py`, distribution-build verification |
| `REQ-PKG-006` | `tests/test_project_metadata.py`, `.github/workflows/ci.yml`, `tools/verify_wheel.py`, distribution-build verification |
| `REQ-PKG-007` | `tests/test_project_metadata.py`, `.github/workflows/ci.yml`, `tools/verify_wheel.py`, distribution-build verification |
| `REQ-PKG-008` | `tests/test_project_metadata.py`, `.github/workflows/ci.yml`, `tools/verify_wheel.py`, distribution-build verification |
| `REQ-PKG-009` | `tests/test_project_metadata.py`, `.github/workflows/ci.yml`, `tools/verify_wheel.py`, distribution-build verification |
| `REQ-PKG-010` | `tests/test_project_metadata.py`, `.github/workflows/ci.yml`, `tools/verify_wheel.py`, distribution-build verification |
| `REQ-REPO-001` | `tests/test_project_metadata.py`, source-archive inventory and clean-tree delivery checks |
| `REQ-REPO-002` | `tests/test_project_metadata.py`, source-archive inventory and clean-tree delivery checks |
| `REQ-REPO-003` | `tests/test_project_metadata.py`, source-archive inventory and clean-tree delivery checks |
| `REQ-REPO-004` | `tests/test_project_metadata.py`, source-archive inventory and clean-tree delivery checks |
| `REQ-REPO-005` | `tests/test_project_metadata.py`, source-archive inventory and clean-tree delivery checks |
| `REQ-REPO-006` | `tests/test_project_metadata.py`, source-archive inventory and clean-tree delivery checks |
| `REQ-REPO-007` | `tests/test_project_metadata.py`, source-archive inventory and clean-tree delivery checks |
| `REQ-DEL-001` | delivery manifest, checksum list, exact-baseline patch application, byte-for-byte reconstruction |
| `REQ-DEL-002` | delivery manifest, checksum list, exact-baseline patch application, byte-for-byte reconstruction |
| `REQ-DEL-003` | delivery manifest, checksum list, exact-baseline patch application, byte-for-byte reconstruction |
| `REQ-DEL-004` | delivery manifest, checksum list, exact-baseline patch application, byte-for-byte reconstruction |

## Environment-dependent evidence

The hosted CI workflow is the intended authority for Python 3.11/3.12/3.13, Ruff, mypy, and dependency-isolated wheel installation. The current local execution environment can still verify Python behavior, source reproduction, packaging structure, patch reconstruction, and benchmark behavior when the required dependencies are already present.

`uv.lock` is not present in this iteration because the current environment cannot resolve the package index. The repository does not ignore it.
