# Changelog

## 0.4.0b6 — 2026-09-20

- Remove per-candidate source churn from the routine release gate. `release-compare.toml` now keeps a stable `__BASELINE__` placeholder; `campaign plan/run/compare/check` require the accepted prior candidate explicitly with `--baseline`, resolve it to an immutable commit, and retain that identity in the existing content-addressed effective plan.
- Remove `benchmarks/release-baseline.toml`. Machine-readable evidence handoffs preserve release-baseline intent through retained effective plans instead of copying a mutable candidate-selection file.
- Make `benchmarks.release_workflow refresh` proportional. The default `release` scope runs only the bounded release comparison/check/report path; `integration` adds smoke; `promotion` adds full-HEAD, sparse dependency, supported-Python, and direct-reference evidence; backward-compatible history and diagnostics are explicit additions.
- Make `docs/benchmark-operations.md` the single maintained executable benchmark runbook. Root/user/testing/benchmark architecture documents now link to that runbook rather than duplicating current ASV workflow commands, and remaining migration-era active instructions are removed.
- Add `DEC-064` and update `REQ-PERF-021`/`REQ-PERF-024` to distinguish stable campaign configuration from explicit release-decision input and to require proportional evidence selection. Runtime lookup behavior, benchmark case semantics, timing bodies, environment profiles, normalized-evidence algorithms, and the release threshold are unchanged.

## 0.4.0b5 — 2026-09-19

- Address isolated b4 benchmark/documentation review findings FEREGION-001 through FEREGION-006 without changing runtime lookup behavior or benchmark timing semantics.
- Replace the stale `v0.4.0a9` routine release baseline with the explicitly accepted prior candidate `v0.4.0b4`, recorded in `benchmarks/release-baseline.toml`; repository tests require `release-compare.toml` to stay synchronized with that baseline policy.
- Retain one content-addressed effective campaign plan for every benchmark run under `.asv/feregion-plans/`, including resolved revisions, effective repetitions/rounds, sample and append policy, machine/comparability policy, requested report steps, source-config hash, and operator ASV/asv-runner identity. Revision-run records link to the plan digest.
- Populate normalized evidence with the operator ASV identity from retained run records and the observed `asv-runner` identity from benchmark-environment verification when available; include plan records plus the release-baseline source in machine-readable evidence handoffs. Historical records that predate the new provenance schema may keep null tool identities.
- Reconcile maintained benchmark-authority status across requirements, design, quality assurance, traceability, README, migration-parity, and roadmap documentation; give the migration-authority decision the unique ID `DEC-062` and add repository checks for decision-ID uniqueness and authority-state synchronization.
- Make the ASV-installed CI job execute the focused benchmark contract pytest module so the direct ASV parser oracle cannot silently skip there. CI now plans the `smoke` campaign instead of requiring locally maintained historical tags merely to validate the benchmark source contract; historical tag availability remains an operator/repository-state requirement for historical campaigns.

## 0.4.0b4 — 2026-09-19

- Close `REQ-PERF-017` from the reviewed post-b3 benchmark-evidence checkpoint. The retained normalized `release-compare` evidence contains all seven required loads for both `0.4.0a9` and b3 under the same `uv-py3.12-numpy1.26.4-pandas2.1.4` environment, and the project throughput gate is complete with no trigger.
- Accept the retained post-b3 report-rebuild evidence: `asv publish --no-pull --config asv.conf.json` returned success, produced an HTML index with 127 files, and recorded the exact source-evidence digest used for the rebuild.
- Promote ASV to the primary benchmark-evidence path for the completed `0.4` migration. Keep the standalone timer, `pytest-benchmark`, Tox Python matrix, and predecessor comparator runnable as compatibility/reference tooling and retained provenance rather than as a second co-equal benchmark authority.
- Reconcile maintained benchmark results, migration parity, quality/traceability, operator guidance, roadmap, and report metadata with the accepted post-b3 evidence checkpoint. Remaining high-load resource attribution and reporting/archival enhancements stay non-blocking investigation or roadmap work.
- Keep runtime lookup behavior, benchmark timing semantics, normalized-evidence algorithms, and the release threshold unchanged; b4 is an evidence/authority closeout patch plus prerelease-version advance.

## 0.4.0b3 — 2026-09-19

- Bind normalized campaign evidence to the campaign's declared ASV environment profile. A release check can no longer relabel same-case timings from `reference-comparison` or another profile as `release-compare` evidence.
- Retain local ASV report-rebuild records under `.asv/feregion-reports/`, including the report command outcome, source-evidence content digest, and resulting HTML presence/count; include these records in machine-readable evidence handoffs.
- Reconcile the post-b2 benchmark evidence: the corrected reference profile is verified and produces a finite direct ObsPy result, fresh b2 standalone/pytest-benchmark/Tox evidence is retained, and the earlier normalized release-check output is rejected because its candidate rows came from the reference environment rather than the release-history profile.
- Clarify migration closure: `REQ-PERF-009` requires failure states to remain distinguishable, not deliberate corruption of every real benchmark environment. Existing controlled integration fixtures cover rare failure-state normalization; genuine historical `not_applicable` and real environment-integrity evidence remain preserved.
- Keep `REQ-PERF-017` open until b3 is applied and a clean same-profile `release-compare` check plus retained report-rebuild record are produced and reviewed.

## 0.4.0b2 — 2026-09-19

- Add `python -m benchmarks.evidence_bundle` as the human-operator command for a machine-readable benchmark handoff. The ZIP preserves raw ASV results, setup state, revision-run records, environment-integrity records, normalized evidence, predecessor benchmark outputs, campaign configuration, and repository identity while excluding rebuildable `.asv/html`.
- Add ASV environment-integrity preflight. Before timing is accepted, the benchmark process now compares `asv-env-info.json` requested versions with installed distributions, imports requested benchmark dependencies, runs `pip check`, and retains the observed result under `.asv/feregion-environments/`. Environment drift is recorded as `build_unavailable` rather than as a valid timing.
- Repair the `reference-comparison` profile after the b1 investigation reproduced an invalid environment: ObsPy 1.4.2 was installed but failed because Setuptools 84 no longer supplied `pkg_resources`, while NumPy had drifted from requested 1.26.4 to 2.5.3. Apply an explicit reference-comparison pip constraint set for NumPy 1.26.4, pandas 2.1.4, ObsPy 1.4.2, and Setuptools 81.0.0 to every ASV environment-install subprocess; the environment preflight then verifies the final installed state before timing.
- Stop treating failure to import explicitly requested ObsPy as a normal capability absence. The ObsPy comparator remains `not_applicable` when the selected ASV profile does not request ObsPy; a broken requested reference environment is now retained as environment failure and causes benchmark execution to fail.
- Reconcile maintained benchmark documentation with the supplied b1 ASV preservation set: real smoke, release, history, dependency, supported-Python, reference, and diagnostic campaigns are recorded; source-reference and diagnostic cases are measured; real `correctness_passed` and historical `not_applicable` states are observed; direct b1 ObsPy timing remains invalid pending rerun under the corrected profile; and the partial `head-full` result remains incomplete.
- Preserve `REQ-PERF-017` and predecessor benchmark authority. b2 improves the evidence substrate and documentation but does not claim migration parity, release validation, or a current like-for-like ObsPy speed result until the corrected reference campaign and predecessor reconciliation are rerun.

## 0.4.0b1 — 2026-09-19

- Promote the `0.4` benchmark-system target to beta maturity without changing runtime lookup behavior or the a10 benchmark algorithms. The a10 source already addresses isolated-review findings FREG-001 through FREG-005; b1 is a stabilization and verification candidate rather than a second implementation of those fixes.
- Incorporate maintainer-host ASV evidence acquired after a10: exact `v0.4.0a10`/HEAD identity was resolved to `665d3c85d537155cbeae417f80a8a572048dd9a0`, current and historical numeric cases executed, and a controlled `0.1.2a10`/`0.2.0b1`/`0.3.0b1` rerun found geographic batch performance approximately flat while `0.3.0b1` seismic batch lookup is materially faster than `0.2.0b1` at large loads.
- Keep `REQ-PERF-017` open. The supplied result handoff still lacks current measurements for the restored direct ObsPy/source reference cases, split/stack diagnostics, and pandas in-place cases, and it does not demonstrate the complete real failure-state/report-rebuild parity contract. The predecessor standalone/pytest-benchmark/Tox/release-comparator path therefore remains authoritative.
- Record memory-pressure limits explicitly: a prior broad run entered swap, and the controlled historical rerun did not retain swap-I/O telemetry. Large name/pandas measurements remain investigation evidence unless resource state is recorded; small percentage differences are not promoted into regression claims.
- Advance project/package maturity metadata from alpha to beta while keeping release validation, benchmark-authority migration, external-source/oracle checks, static/multi-Python checks, and publication approval as separate evidence states.

## 0.4.0a10 — 2026-09-18

- Address isolated benchmark review findings FREG-001 through FREG-005: replace shape/range-only ASV acceptance with bounded pinned-source semantic checks, preserve stored ASV benchmark-version identity, correct the release gate to compare throughput slowdown, retain explicit setup/run failure-state evidence, and synchronize maintained implementation-state documentation.
- Restore ASV migration coverage for predecessor benchmark roles, including direct ObsPy and pinned-source comparators, seismic-name conversion, pandas in-place paths, private split-vector and caller-stacking diagnostics; add maintained reference-comparison and diagnostic campaigns.
- Retain operations-per-second as a first-class normalized evidence field and release-comparison metric instead of treating elapsed duration as the project performance decision quantity.
- Reclassify ASV as a secondary migration candidate for the remainder of the 0.4 alpha: the standalone timer, pytest-benchmark suite, Tox Python benchmark matrix, and predecessor release comparator remain the current benchmark authority until semantic/case parity and real vertical-slice evidence satisfy REQ-PERF-017.
- Record that the retained historical snapshot shows the early 0.1.2a10→0.2.0b1 slowdown was followed by recovery/improvement rather than persistent monotonic degradation, while explicitly declining to infer that it was a one-time causal event from the available single-host evidence.

## 0.4.0a9 — 2026-09-18

- Fix seven Ruff E501 findings in ASV benchmark metadata, reporting HTML insertion, and benchmark contract-test documentation without changing benchmark semantics or reporting behavior.
- Advance the package candidate after the formatting/lint normalization and keep maintained verification wording aligned with the a9 candidate.

## 0.4.0a8 — 2026-09-18

- Improve ASV's existing information surface with human-readable benchmark names and timing-contract source descriptions, while preserving project-owned semantic case versions.
- Add a local ASV `OutputPublisher` plugin that creates an additive `feregion summary` page with environment/revision coverage, ASV regression-signal context, and curated load-scaling links without replacing ASV's native graphs or modifying the installed ASV package.
- Add `benchmarks.release_workflow` for repeatable current-release benchmark population, retained-evidence report rebuild/preview, and explicitly authorized GitHub Pages publication; campaign runs now accept repetition/round overrides and ASV raw-sample append mode.
- Fix retained-ASV sample normalization when an earlier parameter value has no samples but a later parameter does, matching ASV v2's parameter-list contract instead of inspecting only the first sample entry.
- Add maintained benchmark-results, ObsPy-versus-feregion selection, benchmark-roadmap, and expanded operator documentation based on the populated ASV evidence supplied during final-alpha development.
- Expand the sparse dependency-matrix release refresh to retain both pandas numbers-only and numbers-plus-names evidence, include the reporting JS/CSS in source distributions, and document the higher-round sample-append workflow and its intentionally non-uniform sample counts.

## 0.4.0a7 — 2026-09-18

- Expand the maintained batch benchmark load contract to the 1-2-5 engineering grid from 1 through 50,000,000 points, with regression adjacency defined by that maintained order rather than by whichever observations happen to exist.
- Add maintained predefined campaigns for smoke, full-suite `HEAD`, routine release comparison, backward-compatible release history, supported Python versions, NumPy sensitivity, pandas sensitivity, and a bounded sparse dependency matrix.
- Add `benchmarks.campaign check` to reconstruct normalized project evidence from retained ASV v2 result files without rerunning measurements, apply the project >25% two-adjacent-load release rule, and return distinct pass/trigger/incomplete statuses.
- Add a human benchmark-operations runbook covering campaign rationale, per-iteration reruns, high-memory load cautions, evidence retention, report regeneration/preview, and an explicit GitHub Pages publication procedure.
- Update benchmark requirements, design, decisions, quality gates, traceability, testing guidance, and operator quick reference for the a7 workflow.

## 0.4.0a6 — 2026-09-18

- Resolve every campaign revision identity to an immutable Git commit before ASV execution; `run` now passes `<resolved-commit>^!` so one campaign revision cannot expand into its first-parent history, while `compare` uses the resolved commit identities.
- Reject Git range/revision-expression syntax such as `HEAD^!`, `main..HEAD`, and `HEAD~1` in campaign configuration and fail missing refs during preflight before ASV creates environments or builds packages.
- Make the ASV project-build ownership boundary explicit in both persistent and generated configuration: build the `feregion` wheel with `pip wheel --no-deps` and install it with `pip install --no-deps --force-reinstall`, leaving NumPy/pandas selection to the ASV environment matrix and preserving a single-wheel `{wheel_file}` cache.
- Extend benchmark contract tests with real temporary-Git history checks, immutable resolved-plan evidence, explicit ASV build/install command checks, and regression coverage for the two user-observed ASV integration failures.
- Update benchmark requirements, design, quality gates, traceability, decisions, testing guidance, and operator documentation around the full revision → build → install → discovery boundary.

## 0.4.0a5 — 2026-09-18

- Local maintainer diagnostic candidate used to reproduce the ASV revision-selection and build-cache failures that are corrected in `0.4.0a6`; no additional functional change is asserted here because the exact a5 handoff was not supplied to this implementation environment.

## 0.4.0a4 — 2026-09-18

- Fix the campaign-to-ASV subprocess contract after a real `local-smoke` run exposed that the generated command used an unsupported pre-subcommand `-c` form; commands now use ASV's documented subcommand-local `--config` option.
- Generate temporary campaign ASV configuration in the repository root because ASV changes its working directory to the configuration-file directory; this keeps relative benchmark, environment, result, and HTML paths anchored to the repository and removes the temporary file after execution.
- Isolate ASV discovery under `benchmarks/asv_suite/` so the ASV runner imports only benchmark-runner-safe modules and does not import the retained predecessor `pytest-benchmark` module or unrelated benchmark tooling.
- Make partial load-size selection exact so selecting `100` no longer also matches `1_000`, `10_000`, `100_000`, or `1_000_000` through decimal-prefix regex matches.
- Add subprocess-boundary regression coverage for ASV argument order, generated-config location/lifetime, dedicated-suite isolation, exact parameter filtering, and ASV's own parser when the benchmark dependency is installed.
- Update the benchmark requirements, design, quality gate, decision ledger, traceability, and operator documentation to record the external-tool boundary and the remaining requirement for a real ASV smoke/vertical-slice run.

## 0.4.0a3 — 2026-09-18

- Resolve the remaining Ruff findings in the ASV benchmark bindings and regression comparison by marking intentional mutable ASV class attributes as `ClassVar` and using `itertools.pairwise()` for adjacent load comparisons.
- Change the default clean-handoff destination to `dist/` and include the package version and UTC date in the archive name: `feregion-v<version>-<YYYY-MM-DD>-handoff.zip`; derive the canonical archive prefix and internal `feregion/` root from project metadata rather than the local checkout-directory name, while retaining explicit `--output` support.
- Add handoff-export regression coverage and update repository requirements, design, decision, traceability, and maintainer documentation for the new archive location and identity.
- Correct benchmark documentation that still described the implemented `0.4` ASV system as only a future `0.3`-baseline plan.

## 0.4.0a2 — 2026-09-18

- Apply the maintainer-provided Ruff formatting pass and safe autofixes across the `0.4.0a1` source candidate; no intentional public runtime behavior change is recorded for this maintenance candidate.

## 0.4.0a1 — 2026-09-17

- Introduce the benchmark-focused `0.4` line with ASV 0.6.x as the generic revision/environment/timing/history/static-report substrate while keeping benchmark semantics and release decisions project-owned.
- Add stable benchmark case/version contracts, deterministic workloads, historical public-interface adapters, ASV benchmark bindings, named sparse Python/NumPy/pandas environment profiles, TOML campaigns, and a thin `plan`/`run`/`compare`/`report` operator CLI.
- Add a normalized project benchmark-evidence schema and retain the existing greater-than-25-percent slowdown-at-two-adjacent-loads release-review rule as a project-owned decision rather than an ASV regression heuristic.
- Keep predecessor benchmark tooling temporarily as migration evidence until the required ASV vertical-slice parity and static-site checks can be executed; ASV execution remains unverified in this delivery environment because external package resolution is unavailable.
- Update benchmark requirements, design, decisions, quality gates, verification traceability, testing guidance, and operator documentation to the implemented `0.4.0a1` architecture.

## 0.3.0b1 — 2026-09-13

- Promote the `0.3` target to beta after a CPS- and software-quality-guided self-review found the intended target functionality substantially complete and no remaining alpha-stage design blocker.
- Reconfirm the performance-focused `0.3` rationale on CPython 3.13 with a controlled same-process comparison against the accepted `0.2` beta baseline: the unchanged geographical matrix path remains approximately flat while seismic batch lookup is about 2.0–3.0x faster and the internal split-vector geographical path about 1.5–1.7x faster at 10k–1M points on the measured host.
- Add an executable maturity-metadata consistency check so prerelease stage, PyPI development-status classifier, quality-assurance status, and verification-traceability status cannot drift silently.
- Keep beta maturity separate from release validation: hosted CI for the exact beta candidate, release-specific `QG-PERF`, exact-candidate external-source/oracle reruns, and qualified source-data redistribution disposition remain explicit evidence or authority items.

## 0.3.0a4 — 2026-08-31

- Make plural region-number conversion APIs honor their published NumPy-array return contract for scalar `ArrayLike` input by returning zero-dimensional arrays instead of NumPy scalar objects.
- Improve CSV failure diagnostics so filesystem failures state that no partial destination was published and stdout failures warn that earlier streamed rows may need to be discarded before retry.
- Correct the README `lookup_region()` representation and document scalar-versus-plural conversion behavior.
- Expand caller-facing docstrings for the explicit public lookup, conversion, default-engine, value-type, and GeoJSON-write interfaces.
- Retain the `0.3.0a3` scientific assets, coordinate semantics, hierarchy, and batch-optimization implementation unchanged.

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
