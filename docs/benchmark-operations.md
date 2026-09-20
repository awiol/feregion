# Benchmark operations

This guide explains how to operate the `feregion` ASV benchmark system and why each step exists. The benchmark harness is development tooling, not runtime API.


## Benchmark authority in 0.4

Reviewed post-b3 evidence satisfies `REQ-PERF-017`. ASV plus the project-owned
campaign/evidence/regression layers are the primary release-performance authority for
`0.4`. The predecessor standalone timer, `pytest-benchmark` suite, Tox Python matrix,
and release comparator remain runnable for compatibility, investigation, and historical
provenance. See `benchmark-migration-parity.md`.

Authoritative ASV setup additionally requires the hash-verified pinned FE source
tables because benchmark correctness is checked against the independent source
scanner before timing:

```bash
uv run --locked python -m tools.fetch_obspy_fe_data
```

Normalized ASV evidence retains both elapsed seconds and derived
`operations_per_second` for throughput-capable cases. Release decisions use throughput
slowdown, not duration increase.

## 1. Mental model

The benchmark system has two owners:

- `feregion` owns benchmark semantics, deterministic workloads, historical compatibility adapters, campaign intent, normalized evidence, the project-specific regression decision, and a small project summary page.
- ASV owns environment creation, historical package build/install, timing, raw samples, result history, generic graphing, regression detection, and static-site generation.

A campaign is an operator-facing request. A result file is measurement evidence. A report is a derived view over retained results. Publishing changes external state and is a separate action.

Do not infer a performance regression from measurements made on different machines or dependency environments unless a declared comparison contract explicitly permits it. ASV's native Regressions page is a sensitive investigation surface. The project release gate is `python -m benchmarks.campaign check` and uses the stricter `feregion` rule.

## 2. Maintained load grid

Batch benchmarks support the 1-2-5 engineering grid from 1 through 50,000,000 points:

```text
1, 2, 5,
10, 20, 50,
100, 200, 500,
1,000, 2,000, 5,000,
10,000, 20,000, 50,000,
100,000, 200,000, 500,000,
1,000,000, 2,000,000, 5,000,000,
10,000,000, 20,000,000, 50,000,000
```

The grid is a supported benchmark-input contract, not a promise that every host can run every case. The raw coordinate matrix for 50,000,000 points alone is about 800 MB as `float64`, before results, pandas objects, ASV process overhead, or allocator overhead. Use `head-full` only on a host with enough memory. Resource exhaustion is infrastructure evidence, not a valid timing measurement.

## 3. Predefined campaigns

The repository maintains these canonical campaigns under `benchmarks/campaigns/`:

| Campaign | Purpose | Normal use |
| --- | --- | --- |
| `smoke.toml` | Small `HEAD` integration run | First real-ASV check after benchmark-system or packaging changes |
| `release-compare.toml` | Explicit accepted baseline versus `HEAD` on the fixed release environment | Routine bounded regression gate before a new candidate |
| `release-history.toml` | Backward-compatible history across representative package generations | Periodic/public history and adapter validation |
| `head-full.toml` | Every maintained case over the complete 1-2-5 load grid on `HEAD` | High-confidence/full-scale runs; intentionally expensive |
| `numpy-sensitivity.toml` | Selected NumPy versions on `HEAD` | Focused NumPy support/performance investigations |
| `pandas-sensitivity.toml` | Selected pandas versions on `HEAD` | Focused pandas adapter investigations |
| `python-supported.toml` | Supported CPython versions on `HEAD` | Interpreter sensitivity/support checks |
| `dependency-matrix.toml` | Sparse maintained NumPy/pandas union | Promotion/support evidence without a full Cartesian product |
| `reference-comparison.toml` | Direct ObsPy and pinned-source comparison | Reference/oracle investigations and promotion evidence |
| `diagnostics.toml` | Split-vector, caller-stacking, and pandas in-place diagnostics | Targeted investigation only |

`release-compare.toml` intentionally contains the stable `__BASELINE__` placeholder.
The operator must supply the accepted prior candidate with `--baseline`. The CLI resolves
that identity to an immutable commit and retains it in the content-addressed effective
plan before timing begins. The repository does not infer the baseline from tag ordering
and does not require a source edit merely because a new candidate was accepted.

The focused NumPy and pandas campaign files remain useful for targeted investigations.
The promotion workflow uses the sparse `dependency-matrix` campaign instead so it can
populate the maintained union in one pass.

## 4. Prepare one machine

Use a stable benchmark host when results will support a release decision. Avoid comparing results across changing power policies, heavy background workloads, containers with materially different CPU quotas, or different physical machines.

Install the locked benchmark environment and validate the ASV suite:

```bash
uv sync --locked --group benchmark
uv run --locked --group benchmark asv --version
uv run --locked --group benchmark asv check --config asv.conf.json
```

ASV records machine metadata in its normal machine configuration. Keep the machine identity stable for results that will be compared over time.

## 5. Inspect before measuring

Always plan a maintained campaign before running it:

```bash
uv run --locked --group benchmark \
  python -m benchmarks.campaign plan benchmarks/campaigns/smoke.toml
```

`plan` does not benchmark anything. It validates cases/load sizes/profile names, resolves every requested Git identity to one immutable commit SHA, and prints the exact campaign contract. This catches missing tags and accidental Git range syntax before ASV creates environments or builds packages.

For authoritative runs, the CLI automatically writes one content-addressed effective plan under `.asv/feregion-plans/` before timing begins. Revision-run records link to that plan, including effective timing overrides, sample-append mode, machine/comparability policy, report requests, source-config hash, and benchmark-tool identity.

## 5a. Diagnose historical-tag visibility

Historical and release-comparison campaigns require their named Git revisions to exist in
the checkout. The CI benchmark-contract job validates source/tool integration with the
`smoke` campaign and therefore does not depend on locally maintained historical tags. A
workflow that actually runs historical campaigns still needs those tags on the remote it
checks out.

If a local tag push reports success but GitHub or another runner cannot resolve the tag,
compare the fetch and push destinations instead of repeating the benchmark command:

```bash
git remote get-url --all origin
git remote get-url --push --all origin
git config --get-all remote.origin.pushurl || true
git show-ref --tags | grep 'refs/tags/v0.4.0' || true
git ls-remote --tags origin 'refs/tags/v0.4.0*'
```

A tag that is visible in `git show-ref` but absent from `git ls-remote` was not created on
the remote queried by `origin`. If `git push` reports success while those commands refer to
different URLs, inspect `remote.origin.pushurl` or another push target. A server-side tag
rule normally rejects the push explicitly; do not treat a local `Everything up-to-date`
message against a different push destination as proof that the public repository contains
the tag.

## 6. Run the smoke campaign

Run this after changing packaging, the benchmark harness, historical adapters, or ASV configuration:

```bash
uv run --locked --group benchmark \
  python -m benchmarks.campaign run benchmarks/campaigns/smoke.toml
```

This checks the real path through Git resolution, ASV environment construction, project-only wheel build, installation, benchmark discovery, correctness setup, timing, raw-sample recording, and result persistence. A passing unit test of the wrapper is not a substitute for this integration check.

Inspect retained results when useful:

```bash
uv run --locked --group benchmark asv show HEAD --config asv.conf.json
find .asv/results -maxdepth 3 -type f -print
```

## 7. Routine candidate regression workflow

The routine release comparison requires an explicit accepted prior candidate. Use a tag
when it is reliably available on the benchmark host, or use the exact accepted commit SHA.
Do not let the harness guess the baseline from the newest tag.

Plan and measure:

```bash
uv run --locked --group benchmark \
  python -m benchmarks.campaign plan benchmarks/campaigns/release-compare.toml \
  --baseline <accepted-prior-candidate>

uv run --locked --group benchmark \
  python -m benchmarks.campaign run benchmarks/campaigns/release-compare.toml \
  --baseline <accepted-prior-candidate>
```

ASV's generic comparison is useful for inspection:

```bash
uv run --locked --group benchmark \
  python -m benchmarks.campaign compare benchmarks/campaigns/release-compare.toml \
  --baseline <accepted-prior-candidate>
```

The project release gate is separate. It reconstructs normalized evidence from retained
`.asv/results` and applies the maintained >25% throughput-slowdown rule at two adjacent
1-2-5 load sizes of at least 10,000 points:

```bash
uv run --locked --group benchmark \
  python -m benchmarks.campaign check benchmarks/campaigns/release-compare.toml \
  --baseline <accepted-prior-candidate>
```

Exit status is:

- `0`: the comparison is complete and the project regression trigger is not crossed;
- `1`: the comparison is complete and the project regression trigger is crossed;
- `2`: evidence is incomplete or ambiguous.

The command writes normalized evidence under `dist/benchmarks/` by default. Evidence is
bound to the campaign's declared environment profile: same-case results from another
profile are ignored rather than relabeled. If retained results contain more than one
comparable machine, add `--machine <asv-machine-name>` to the `check` command.

A project `check` result is not a causal explanation. Investigate a trigger before
deciding whether it represents code, dependency, machine, or measurement change.

## 8. Populate release evidence with one workflow

`benchmarks.release_workflow` provides one synchronous entry point with proportional
scopes. Every refresh requires the accepted prior candidate explicitly and always runs
the bounded release gate, project check, and report rebuild.

For an ordinary candidate whose change does not require broader benchmark evidence:

```bash
uv run --locked --group benchmark \
  python -m benchmarks.release_workflow refresh --baseline <accepted-prior-candidate>
```

The default `release` scope runs only `release-compare.toml`. It deliberately does not
run the 2M-50M full grid, support matrices, reference comparison, or diagnostics.

For benchmark/package integration changes, add the real smoke path:

```bash
uv run --locked --group benchmark \
  python -m benchmarks.release_workflow refresh \
  --baseline <accepted-prior-candidate> --scope integration
```

For a promotion or other decision that requires the broader maintained portfolio:

```bash
uv run --locked --group benchmark \
  python -m benchmarks.release_workflow refresh \
  --baseline <accepted-prior-candidate> --scope promotion
```

`promotion` adds smoke, full `HEAD`, sparse dependency, supported-Python, and direct
reference-comparison campaigns. Add backward-compatible history only when required:

```bash
uv run --locked --group benchmark \
  python -m benchmarks.release_workflow refresh \
  --baseline <accepted-prior-candidate> --scope promotion --history
```

Diagnostics are investigation evidence and are never implicit. Add `--diagnostics` only
when the decision needs them.

Measurement controls remain available for evidence strengthening:

```bash
uv run --locked --group benchmark \
  python -m benchmarks.release_workflow refresh \
  --baseline <accepted-prior-candidate> --scope promotion \
  --repetitions 15 --rounds 7 --append-samples
```

`--repetitions` and `--rounds` override campaign timing controls for that execution.
`--append-samples` combines new raw samples only with compatible retained cells. Do not
append after changing benchmark semantics, workload definition, revision identity, or
comparison environment.

The wrapper never publishes externally. It rebuilds the report even when the project
release check returns a regression trigger or incomplete-evidence status because the
report is useful for investigation; the workflow then returns the project-check status
unless report generation itself fails.

## 9. Backward-compatible historical benchmarking

The maintained historical campaign deliberately includes releases from different API generations:

```bash
uv run --locked --group benchmark \
  python -m benchmarks.campaign plan benchmarks/campaigns/release-history.toml

uv run --locked --group benchmark \
  python -m benchmarks.campaign run benchmarks/campaigns/release-history.toml
```

Modern benchmark definitions remain in control while ASV installs each selected historical package revision. The project adapter maps stable semantic cases to historical public interfaces. A capability that genuinely did not exist is skipped/not applicable; it must not be emulated or silently replaced by a different operation.

Historical campaigns are not expected to make every benchmark available at every revision. Missing capability and infrastructure/build failure are different states and must remain distinguishable.

## 10. Full HEAD and sensitivity campaigns

The routine release gate intentionally stops at 1,000,000 points so it remains practical to rerun on every candidate. The upper 2M–50M scaling points belong to `head-full` or a purpose-built investigation campaign.

The complete current implementation can be measured with:

```bash
uv run --locked --group benchmark \
  python -m benchmarks.campaign run benchmarks/campaigns/head-full.toml
```

This is intentionally expensive. Start with `smoke` and use `head-full` when the decision justifies the runtime and memory cost.

Focused dependency/interpreter campaigns are:

```bash
uv run --locked --group benchmark python -m benchmarks.campaign run benchmarks/campaigns/numpy-sensitivity.toml
uv run --locked --group benchmark python -m benchmarks.campaign run benchmarks/campaigns/pandas-sensitivity.toml
uv run --locked --group benchmark python -m benchmarks.campaign run benchmarks/campaigns/python-supported.toml
uv run --locked --group benchmark python -m benchmarks.campaign run benchmarks/campaigns/dependency-matrix.toml
```

The dependency matrix is a sparse union of the maintained NumPy and pandas sweeps. It is not a NumPy×pandas Cartesian product.

## 10a. Reference comparison and targeted diagnostics

Run the current-revision direct comparator campaign when ObsPy-versus-feregion or
source-scanner evidence matters:

```bash
uv run --locked --group benchmark \
  python -m benchmarks.campaign run benchmarks/campaigns/reference-comparison.toml
```

This profile requests ObsPy 1.4.2, NumPy 1.26.4, pandas 2.1.4, and Setuptools 81.0.0.
The campaign wrapper applies `benchmarks/constraints/reference-comparison.txt` as a
process-level pip constraint so ASV's sequential `pip --upgrade` operations cannot
change those requested versions. It measures feregion scalar lookup, direct ObsPy scalar lookup, direct pinned-source
scalar lookup, feregion batch lookup, and the pinned-source batch-equivalent scan on
common deterministic workloads. b2 verifies requested-versus-installed versions,
required imports, and `pip check` before timing is accepted. A broken explicitly
requested ObsPy environment is an environment/build failure, not `not_applicable`.

Run targeted diagnostics with:

```bash
uv run --locked --group benchmark \
  python -m benchmarks.campaign run benchmarks/campaigns/diagnostics.toml
```

These cases retain private split-vector, caller-stacking, and pandas in-place evidence.
They are diagnostic contracts, not public runtime API.

## 10b. Predecessor compatibility/reference tooling

The predecessor benchmark stack is retained for compatibility checks, investigation, and
historical provenance. It is not the primary release-performance authority. Run it only
when that compatibility/reference evidence is needed.

Prepare the verified source cache and benchmark dependencies:

```bash
uv run --locked python -m tools.fetch_obspy_fe_data
uv sync --locked --group benchmark
```

Run the predecessor pytest-benchmark and standalone paths:

```bash
uv run --locked --group benchmark pytest benchmarks --benchmark-only \
  --benchmark-json=benchmark.json
uv run --locked --group benchmark python -m benchmarks.run_benchmark \
  --output benchmark-standalone.json
```

Run its supported-Python compatibility matrix when required:

```bash
uv run --locked --group matrix --group benchmark tox run \
  -e benchmark-py311,benchmark-py312,benchmark-py313,benchmark-py314,benchmark-report
```

A retained predecessor release comparison can be reconstructed from two compatible raw
JSON records:

```bash
uv run --locked --group benchmark python -m benchmarks.compare_releases \
  --baseline baseline.json --candidate candidate.json --fail-on-trigger
```

Do not use this compatibility path as a second release authority. Preserve its final
machine-readable evidence when it materially supports investigation or historical review.

## 11. Rebuild and understand the report without rerunning measurements

Retained `.asv/results` are the measurement history. `.asv/html` is derived output. Rebuild the complete site from all retained measurements with:

```bash
uv run --locked --group benchmark \
  python -m benchmarks.release_workflow report
```

This delegates to `asv publish --no-pull`; it does not run benchmarks. The local feregion ASV plugin adds:

- human-readable benchmark display/source metadata used by ASV;
- a `feregion summary` page beside the native ASV views;
- benchmark/revision/regression counts;
- environment coverage;
- recent tags/commits; and
- curated links that open parameterized benchmarks with `size` as the x-axis.

The extension is additive. Native ASV Grid/List/Graph/Regressions views remain the detailed technical explorer. The project does not modify the installed ASV package.

To prove that report generation is independent from measurement, remove only derived HTML and rebuild:

```bash
rm -rf .asv/html
uv run --locked --group benchmark python -m benchmarks.release_workflow report
```

Preview through ASV's local HTTP server rather than opening `index.html` directly:

```bash
uv run --locked --group benchmark \
  python -m benchmarks.release_workflow preview
```

Inspect the project summary, benchmark descriptions, scaling views, revision/tag history, environment selectors, missing/skipped values, and native Regressions page before publication.

Do not delete `.asv/results` merely because a report was built. For reproducibility,
preserve `.asv/results`, `.asv/feregion-state`, `.asv/feregion-runs`,
`.asv/feregion-plans`, `.asv/feregion-environments`, and `.asv/feregion-reports` together. The sidecars retain
correctness, failure-state, requested-versus-observed environment meaning, and local
report-rebuild provenance that raw ASV timing JSON does not encode by itself.

Create one machine-readable handoff without derived HTML with:

```bash
uv run --locked --group benchmark python -m benchmarks.evidence_bundle
```

The command writes a timestamped ZIP under `dist/benchmarks/` by default. Use
`--output PATH.zip` when another destination is required. The archive contains a JSON
manifest with SHA-256 values and present/missing evidence-family status, available raw
ASV results/state/run/environment/report records, normalized evidence, predecessor
benchmark outputs, campaign definitions, configuration, and repository identity. Missing
optional evidence families remain explicit and do not prevent creating a partial handoff.
Generated `.asv/html` remains excluded because the retained report record proves the
local rebuild outcome without treating derived HTML as authoritative evidence.

## 12. Publish to GitHub Pages

Publishing is an external state change. Benchmark completion and report generation do not authorize or prove publication.

Prerequisites:

1. The intended benchmark results are retained and reviewed.
2. `python -m benchmarks.release_workflow report` succeeds.
3. `python -m benchmarks.release_workflow preview` shows the expected summary/history/regressions.
4. The Git remote named `origin` points to the intended repository.
5. Repository GitHub Pages settings are configured to serve the `gh-pages` branch (or the project has an equivalent approved static-host workflow).
6. You have authority to update the publication branch.

Stage/update the local `gh-pages` branch without pushing:

```bash
uv run --locked --group benchmark \
  python -m benchmarks.release_workflow publish
```

Review the generated publication commit before external mutation:

```bash
git log -1 --stat gh-pages
git show gh-pages:index.html >/dev/null
```

Publish only with an explicit push option:

```bash
uv run --locked --group benchmark \
  python -m benchmarks.release_workflow publish --push
```

The `--push` form lets ASV update and push the `gh-pages` branch to `origin`. As an alternative after local staging/review, an operator may use `git push origin gh-pages` directly.

Verify remote state:

```bash
git ls-remote --heads origin gh-pages
```

Finally open the repository's configured GitHub Pages URL and verify that the expected project summary, latest revision/tag, benchmark graphs, and regression page are visible. Record the observed URL/commit/time when publication status matters to a delivery or release claim.

Do not use the published branch as a substitute for preserving `.asv/results`: the published site is derived presentation, not the complete measurement evidence.

## 13. Observed evidence and interpretation

`docs/benchmark-results.md` records the current bounded evidence snapshot, including Python, NumPy, pandas, release-to-release behavior, absolute batch timings, and the distinction between native ASV regression signals and the project gate.

`docs/obspy-or-feregion.md` translates the available package capabilities and benchmark evidence into user selection guidance without claiming an unmeasured direct speedup over ObsPy.

`docs/benchmark-roadmap.md` records planned or investigatory harness/reporting work that is not part of the implemented contract.

These documents are supporting evidence/guidance. Retained ASV result/state/run/
environment/report evidence is the raw measurement and provenance basis for the primary
`0.4` benchmark path. Predecessor standalone/pytest/Tox evidence remains retained for
compatibility checks, investigation, and historical comparison.

## 14. Per-iteration checklist

For a routine new alpha/beta candidate:

1. Commit the candidate source. ASV benchmarks commits, not uncommitted working-tree edits.
2. Identify the explicitly accepted prior candidate tag or exact commit; do not edit campaign source merely to advance the baseline.
3. Update `release-history.toml` only when the candidate should become part of maintained historical coverage.
4. Run `asv check` and a real `smoke` after benchmark/package integration changes.
5. Run the bounded release refresh with `--baseline <accepted-prior-candidate>`; choose `--scope integration` or `--scope promotion` only when the decision needs broader evidence.
6. Add `--history`, `--diagnostics`, or higher repetition/round counts only for a stated evidence need.
7. Inspect `campaign check`; investigate any trigger or incomplete state.
8. Preview the rebuilt site when report presentation is part of the decision.
9. Publish only when authorized; verify resulting external state.
10. Retain effective plans, normalized comparison evidence, and underlying ASV result history needed for later review.

A small documentation-only correction normally does not justify a benchmark refresh at
all. Select the least expensive evidence set that can support the claim being made.

## 15. ASV references used by this runbook

- ASV usage and result-history model: <https://asv.readthedocs.io/en/stable/using.html>
- ASV configuration reference: <https://asv.readthedocs.io/en/stable/asv.conf.json.html>
- ASV command reference, including `compare`, `publish`, `preview`, and `gh-pages`: <https://asv.readthedocs.io/en/stable/commands.html>

The project wrapper remains authoritative for `feregion` campaign semantics and the release gate. These ASV references define the external tool behavior on which the wrapper relies.
