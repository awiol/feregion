# Changelog

## 0.1.1a1 — 2026-08-13

- Fixed the reported Ruff `E402`, `B023`, and `SIM115` findings in benchmark and CLI code.
- Made `uv` the canonical repository workflow for dependency management, checks,
  execution, and builds. Removed the redundant Makefile.
- Moved test, lint, and benchmark tooling into `uv` dependency groups. Preserved
  the previously published `test`, `dev`, and `benchmark` extras for compatibility.
- Removed downloaded ObsPy `*.asc` source tables from version-controlled source.
  Added pinned, SHA-256-verified acquisition into an ignored local cache.
- Kept generated runtime lookup assets version-controlled so installed lookup remains
  offline and self-contained.
- Tightened `.gitignore` for long-term repository maintenance without hiding
  contracts, generated runtime assets, tests, project metadata, or a future `uv.lock`.
- Renamed the current requirements and design documents for version `0.1.1a1`.
  Replaced the stable test-plan filename with `docs/testing.md`.
- Reworked repository documentation with controlled technical language and current `uv` commands.

## 0.1.0-alpha.4 — 2026-08-13

- Made filesystem CSV output transactional and rejected input/output path aliasing,
  preventing truncation and partial-file publication after failure.
- Rejected pandas and CSV output-column collisions instead of silently overwriting
  coordinate, existing, or numeric-region fields.
- Enforced single-flight first initialization so packaged assets are read once and one
  default engine is constructed even under concurrent first use.
- Preserved finite/range exception semantics for extended floating dtypes by
  validating before `float64` narrowing.
- Added direct same-workload batch candidate/reference benchmark evidence.
- Renamed requirements and design to versioned/date-stamped alpha.4 filenames and
  updated repository references.
- Added the delivery-side manifest/checksum/patch evidence required for iterative source handoff.

## 0.1.0-alpha.3 — 2026-08-13

- Made exported source bundles repository-ready by using a stable `feregion/`
  archive root.
- Renamed the canonical project documents to `docs/feregion-requirements.md`
  and `docs/feregion-design.md`.
- Removed per-iteration quality-review and benchmark-result evidence from the
  repository source tree; benchmark harnesses remain source-controlled.
- Made wheel verification derive the wheel filename from `pyproject.toml`
  instead of hard-coding the previous pre-release version.
- Tightened source-distribution inclusion rules for repository metadata and
  stable documentation.

## 0.1.0-alpha.2 — 2026-08-13

- Changed scalar coordinate lookup to validate and index the dense table directly
  instead of constructing a one-row NumPy batch.
- Kept batch lookup as the performance-oriented interface; no Rust backend was
  added.
- Added a dedicated optional `benchmark` dependency extra.
- Expanded repository benchmark harnesses to cover scalar, NumPy, name-conversion,
  and pandas interfaces while excluding CLI and GeoJSON timing.
- Added a benchmark-results comparison table and retained raw benchmark evidence.

## 0.1.0-alpha.1 — 2026-08-13

Initial implementation.

- Added scalar FE region-number and `Region` lookup.
- Added vectorized `(n, 2)` NumPy lookup returning `uint16` region numbers.
- Added separate vectorized region-number-to-name conversion.
- Added optional pandas DataFrame adapter with optional name output.
- Added process-wide cached generated assets and default engine.
- Added source-data regeneration and provenance metadata.
- Added point and chunked CSV CLI operations.
- Added optional lookup-equivalent GeoJSON for 754 active FE regions.
- Added exact custom error contracts, focused pytest coverage, source-table oracle
  comparison, optional ObsPy oracle comparison, and automated benchmarks.
