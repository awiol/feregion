# Changelog

## 0.3.0a3 — 2026-08-31

- Replaced seismic GeoJSON parallel child-number/name properties with structured `geographic_regions` number/name objects.
- Added `--properties NAME [NAME ...]` and `--properties all` to the GeoJSON CLI while preserving repeatable `--property`.
- Expanded README GeoJSON examples for CLI and Python API usage.


## 0.3.0a2 — 2026-08-31

- Fix seismic GeoJSON cross-level child enumeration so populated inactive
  geographical crosswalk slots remain excluded by the engine's active-ID rule.
- Keep explicit custom-engine GeoJSON support while making collection provenance
  conditional: FE-1995 scheme/revision metadata is emitted only for the packaged
  default engine; other explicit engines use null scheme/revision values.
- Add custom-engine GeoJSON regression coverage for inactive hierarchy slots and
  provenance-neutral metadata.
- Make README/testing verification commands consistently lock-preserving under
  `REQ-PKG-017` and add a repository consistency test for those examples.
- Make the historical compatibility comment release-neutral.

## 0.3.0a1 — 2026-08-31

- Optimize coordinate-to-seismic batch lookup by applying the validated engine hierarchy directly to geographical numbers produced by the same engine, while retaining full validation for caller-supplied geographical-number conversion.
- Add package-internal split longitude/latitude vector lookup paths and route the pandas adapter through them, avoiding its temporary `(n, 2)` coordinate matrix without adding a new public split-array API.
- Preserve the existing source-dtype FE cell-ownership and exact-boundary semantics in both matrix and split-vector paths; extend the exhaustive grid-index corpus to exercise both representations.
- Add direct internal optimization tests, including exhaustive 64,800-cell trusted seismic equivalence and explicit geographical-only engine failure behavior.
- Extend the benchmark harness with internal split-vector diagnostics while retaining the public release-regression gate separately.
- Classify the iteration as a new minor line because controlled same-process measurements show a material backward-compatible performance change rather than a defect correction; restart prerelease maturity at alpha for stabilization.

## 0.2.0b1 — 2026-08-27

- Make geographical identifier validity active-only: retired or otherwise unused IDs are rejected by direct geographical name and hierarchy operations even when historical/custom name or crosswalk slots are populated.
- Derive explicit-engine active geographical membership from identifiers used by the supplied lookup table.
- Align the distributed scalar typing surface with supported Python and NumPy integer/floating scalar inputs and extend the downstream typing fixture accordingly.
- Add direct negative-path tests for invalid custom hierarchy construction and unsupported pandas hierarchy levels.
- Correct maintained `minimum` tox-environment versus uv `lowest-direct` resolution terminology and broaden `RegionNumberError` documentation to match its public use.
- Separate beta maturity from release-validation status: `0.2.0b1` is a beta-maturity source candidate, while unavailable hosted/source/provenance/performance gates remain explicit and continue to block stronger release claims.
- Keep the split longitude/latitude optimization deferred from this review-closure iteration; optimization work will be rebased separately after the beta baseline is accepted.

## 0.2.0a3 — 2026-08-27

- Fix the Ruff findings reported against the `0.2.0a2` candidate and make mypy a pre-commit check as well as a hosted quality check.
- Run the mypy public-typing gate against Python 3.14 while Ruff and the runtime matrix continue to enforce Python 3.11 compatibility.
- Add exhaustive coordinate-to-grid-index tests for all 64,800 one-degree area cells using center and nearest-representable interior edge/corner values.
- Add previous/exact/next representable-value neighborhoods around every integer longitude/latitude grid intersection, including antimeridian, equator, prime-meridian, and pole semantics.
- Verify quadrant, absolute-latitude index, and absolute-longitude index independently with synthetic probe tables so equal neighboring FE region numbers cannot hide an indexing defect.
- Exercise the exhaustive corpus for `float16`, `float32`, `float64`, and wider `longdouble` where the platform provides additional precision.
- Correct the focused synthetic-table helper documentation: its compact `uint16` values are deterministic but cannot be globally unique over all 65,884 dense-table positions.

## 0.2.0a2 — 2026-08-27

- Fix extended-precision batch lookup so validated coordinate dtypes are preserved through FE cell ownership; scalar, batch, seismic-batch, and pandas routes now agree immediately around integer-degree boundaries.
- Remove the full-size normalized-longitude temporary and implement exact `-180` east-side semantics through quadrant selection without narrowing coordinate values.
- Make the expected ISC hierarchy semantic SHA-256 a literal reviewed source identity rather than a value recomputed from the hierarchy declarations; add scheduled/manual live ISC verification while keeping ordinary tests network-independent.
- Define release-to-release performance-regression evidence around named baseline/candidate benchmark records in the same recorded environment, and add deterministic comparison tooling for the existing greater-than-25-percent adjacent-size review trigger.
- Clarify that WGS84 geographic degrees are a `feregion` package input convention, separate from the historical FE degree-grid definition; the package performs no CRS transformation.
- Expand public-route, extended-precision boundary, pandas, and all-cell-center GeoJSON regression coverage, including predecessor-sensitive tests for the boundary defect.
- Add mypy verification for the shipped inline typing contract while retaining Ruff as the formatting/lint authority.
- Keep the split longitude/latitude public API and further batch-allocation optimization deferred until the corrected implementation is evaluated against controlled benchmark and memory evidence.
- Fixed typing issues found by mypy.

## 0.2.0a1 — 2026-08-27

- Add explicit FE geographical and seismic region APIs while preserving the existing generic API as geographical compatibility behavior.
- Add the 1995 FE 754-to-50 hierarchy as a compact packaged `uint8` crosswalk plus packaged seismic names; normal use remains fully offline.
- Add ISC hierarchy retrieval, normalization, semantic hashing, multi-source provenance metadata schema 3, and generated-asset reproduction support.
- Preserve two-array `FlinnEngdahlLookup` construction as geographical-only and require explicit hierarchy data for seismic capability.
- Extend pandas and CLI adapters with geographical/seismic level selection and level-specific default output names.
- Redesign GeoJSON around independent geometry-level, semantic-property, optional label, and collection-metadata controls; support both 754 geographical and 50 seismic feature collections.
- Move dataset-wide GeoJSON boundary metadata from every feature to one collection-level `feregion` member.
- Add exhaustive hierarchy/cell-grid verification and record `PERF-INV-001` for a future benchmark of already-separated longitude/latitude batch inputs.

## 0.1.2a10 — 2026-08-27

- Fix hosted packaging CI by replacing unsupported `uv build --locked` with `uv build`.
- Keep lock enforcement on `uv sync --locked` and `uv run --locked`, where uv supports it.
- Add a repository-contract regression check that rejects `uv build --locked`.
- Record the corrected build/lock boundary in the engineering requirements and decision ledger.

## 0.1.2a9 — 2026-08-27

- Always recreate the special `minimum` tox environment before resolving lower-bound dependencies.
- Prevent stale tox installer metadata from surviving changes to the minimum environment's runner or installation strategy.
- Keep normal lock-backed compatibility and pre-commit environments reusable for fast local feedback.

## 0.1.2a8 — 2026-08-27

- Route pre-commit behavioral tests through a dedicated tox environment instead of invoking pytest directly.
- Use standard `py311` through `py314` tox environment names and lock-backed normal compatibility environments.
- Make the Python 3.11 minimum-dependency environment resolve the project plus its test extra in one `lowest-direct` uv transaction, avoiding incompatible old-pandas/new-NumPy ABI combinations caused by split resolution.
- Rename benchmark tox environments to explicit `benchmark-py311` through `benchmark-py314` factors and remove an unnecessary Python pin from the report reducer.
- Replace ambiguous Unicode multiplication signs in Python benchmark-report strings and retain the Ruff `capture_output` subprocess cleanup from the maintainer handoff.

## 0.1.2a7 — 2026-08-27

- Add a deterministic Git-tracked working-tree exporter for clean repository handoffs.
- Exclude `uv.lock` from handoff archives even when it is tracked, and warn about non-ignored untracked files that are not exported.
- Add lock-backed tox-uv benchmark environments for Python 3.11 through 3.14.
- Add a compact cross-Python benchmark report for eight representative scalar, batch, name-conversion, and pandas throughput metrics.

## 0.1.2a6 — 2026-08-27

- Fix pandas 2.1 nullable numeric coordinate conversion so missing values reach the core non-finite validation path instead of becoming object-dtype type errors.
- Add a local tox + tox-uv compatibility matrix for Python 3.11 through 3.14.
- Add a Python 3.11 `lowest-direct` environment that derives minimum direct dependencies from project metadata instead of duplicating exact lower-bound versions in CI.
- Reuse the same tox minimum-dependency environment in GitHub Actions.

## 0.1.2a5 — 2026-08-27

- Remove mypy from the project dependency groups and tool configuration.
- Remove mypy from GitHub Actions and repository verification requirements.
- Keep Ruff as the project static-analysis, linting, and formatting authority.
- Keep pytest as the behavioral verification authority.

## 0.1.2a3 — 2026-08-27

- Replace the exact uv executable pin with the compatibility range `uv>=0.10,<1`.
- Let `setup-uv` resolve a compatible uv release from repository metadata instead of forcing one literal version.
- Keep locked CI/pre-commit semantics and full-SHA GitHub Action pins unchanged.
- Change repository tests and maintained documentation to verify uv behavior/range contracts rather than an exact executable version.

## 0.1.2a2 — 2026-08-26

- Add explicit CPython 3.14 support while preserving Python 3.11 as the minimum supported version.
- Harden GitHub Actions with a Python 3.11–3.14 matrix, pinned uv 0.12.6, lock-preserving sync/run commands, workflow concurrency cancellation, and bounded job timeouts.
- Extend repository metadata checks and maintained quality/design documentation for the supported-Python and CI contracts.

## 0.1.2a1 — 2026-08-26

- Adopt stable Git-tracked filenames for maintained requirements, design, decisions, quality assurance, and traceability documents.
- Remove current release version/date banners from maintained documentation.
- Add `pre-commit` to the development toolchain with Ruff format, Ruff check, and pytest hooks.
- Apply the Ruff formatting changes supplied after `0.1.1a3` and the missing NumPy import correction in `tests/test_pandas.py`.
- Synchronize package version metadata to `0.1.2a1`.

## 0.1.1a4 — 2026-08-26

- Ruff-formatting checkpoint recorded by the user-supplied patch; not delivered separately by this workflow.

## 0.1.1a3 — 2026-08-26

- Preserved pandas extended-floating validation semantics by avoiding premature `float64` narrowing in the adapter.
- Converted invalid UTF-8 and strict CSV parser failures into bounded `CsvInputError` CLI failures.
- Added regression-sensitivity evidence for the two corrected boundary defects.
- Added generated-asset hash consistency checks against packaged provenance metadata.
- Strengthened CI with a direct installed-ObsPy oracle job and a declared lower-bound dependency job.
- Strengthened wheel verification to inspect runtime contents, metadata, extras, entry points, and license notices before clean installation.
- Added an explicit quality-assurance plan, release gates, and a versioned decision ledger.
- Expanded public Python docstrings and verification traceability under the current software-quality guidance.

## 0.1.1a2 — 2026-08-23

- Rejected duplicate CSV headers and row-width mismatches instead of silently losing structured input.
- Made CSV and pandas coordinate selectors distinct and unambiguous; pandas now rejects Boolean coordinate columns consistently with the core API.
- Made explicit `FlinnEngdahlLookup` construction own immutable copies of caller-supplied data.
- Defined filesystem CSV output as atomic publication, preserved existing destination permission bits, and restored normal umask semantics for new files.
- Defined packaged region names as ObsPy 1.4.2 `names.asc` values and documented the separate historical naming sources.
- Reframed GeoJSON as area-equivalent one-degree geometry and documented exact boundary-point limitations.
- Pinned ObsPy source acquisition to immutable commit `a629e8c021052904b6b8d62699d03f2a3721ae63` and separated upstream software-license metadata from unresolved FE source-data license provenance.
- Added GitHub Actions verification for Python 3.11, 3.12, and 3.13, Ruff, builds, and dependency-isolated wheel installation.
- Split product, engineering, and repository/delivery requirements while preserving requirement IDs; added verification traceability and synchronization tests.
- Normalized current documentation to the project `must`/`should`/`may`/`can` normative profile and stable terminology.

## 0.1.1a1 — 2026-08-13

- Fixed the reported Ruff `E402`, `B023`, and `SIM115` findings in benchmark and CLI code.
- Made `uv` the authoritative repository workflow for dependency management, checks,
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

- Made filesystem CSV output use atomic publication and rejected input/output path aliasing,
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
- Renamed the current project documents to `docs/feregion-requirements.md`
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
- Added optional one-degree derived GeoJSON for 754 active FE regions.
- Added exact custom error contracts, focused pytest coverage, source-table oracle
  comparison, optional ObsPy oracle comparison, and automated benchmarks.
