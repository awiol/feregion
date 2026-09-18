# Benchmark operations

This guide explains how to operate the `feregion` ASV benchmark system and why each step exists. The benchmark harness is development tooling, not runtime API.

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
| `release-compare.toml` | Previous benchmark candidate versus `HEAD` on the fixed release environment | Routine bounded regression gate before a new candidate |
| `release-history.toml` | Backward-compatible history across representative package generations | Periodic/public history and adapter validation |
| `head-full.toml` | Every maintained case over the complete 1-2-5 load grid on `HEAD` | High-confidence/full-scale runs; intentionally expensive |
| `numpy-sensitivity.toml` | Selected NumPy versions on `HEAD` | Focused NumPy support/performance investigations |
| `pandas-sensitivity.toml` | Selected pandas versions on `HEAD` | Focused pandas adapter investigations |
| `python-supported.toml` | Supported CPython versions on `HEAD` | Interpreter sensitivity/support checks |
| `dependency-matrix.toml` | Sparse union of maintained NumPy and pandas sensitivity environments, including both pandas benchmark paths | Release refresh of dependency evidence without a full Cartesian product |

`release-compare.toml` is intentionally versioned source. When a new benchmark candidate becomes the accepted comparison baseline, update its first revision to that candidate before issuing the next source candidate. Do not silently compare against whichever tag happens to be newest.

The focused NumPy and pandas campaign files remain useful for targeted investigations. The release refresh workflow uses the sparse `dependency-matrix` campaign instead so it can populate the maintained union in one pass.

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

For authoritative work, save or capture the resolved plan with the retained result evidence.

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

Before running `release-compare.toml`, ensure its first revision is the accepted benchmark baseline and its second revision is `HEAD` (or another explicitly selected candidate identity).

Plan and measure:

```bash
uv run --locked --group benchmark \
  python -m benchmarks.campaign plan benchmarks/campaigns/release-compare.toml

uv run --locked --group benchmark \
  python -m benchmarks.campaign run benchmarks/campaigns/release-compare.toml
```

ASV's generic comparison is useful for inspection:

```bash
uv run --locked --group benchmark \
  python -m benchmarks.campaign compare benchmarks/campaigns/release-compare.toml
```

The project release gate is separate. It reconstructs normalized evidence from retained `.asv/results` and applies the maintained >25% slowdown rule at two adjacent 1-2-5 load sizes of at least 10,000 points:

```bash
uv run --locked --group benchmark \
  python -m benchmarks.campaign check benchmarks/campaigns/release-compare.toml
```

Exit status is:

- `0`: the comparison is complete and the project regression trigger is not crossed;
- `1`: the comparison is complete and the project regression trigger is crossed;
- `2`: evidence is incomplete or ambiguous.

The command writes normalized evidence under `dist/benchmarks/` by default. If retained results contain more than one comparable machine, select one explicitly:

```bash
uv run --locked --group benchmark \
  python -m benchmarks.campaign check benchmarks/campaigns/release-compare.toml \
  --machine <asv-machine-name>
```

A project `check` result is not a causal explanation. Investigate a trigger before deciding whether it represents code, dependency, machine, or measurement change.

## 8. Populate a new release with one workflow

For normal release preparation, the repository provides one synchronous wrapper that plans/runs the maintained current-candidate coverage, applies the project release check, and rebuilds the complete ASV report:

```bash
uv run --locked --group benchmark \
  python -m benchmarks.release_workflow refresh
```

The default refresh covers:

1. smoke/integration evidence;
2. previous-candidate versus `HEAD` release comparison;
3. the full `HEAD` benchmark suite and load grid;
4. the sparse dependency matrix, including both pandas paths; and
5. the supported-Python matrix.

Add backward-compatible history when the release or review needs historical evidence:

```bash
uv run --locked --group benchmark \
  python -m benchmarks.release_workflow refresh --history
```

The wrapper deliberately does not publish externally. It rebuilds the report even when the project release check returns a regression trigger or incomplete-evidence status, because that report is needed for investigation; the workflow then returns the project-check status unless report generation itself fails.

### Add more samples instead of replacing compatible retained samples

For stronger repeated evidence on the same revision/environment/case/load cells, use measurement overrides plus ASV sample accumulation:

```bash
uv run --locked --group benchmark \
  python -m benchmarks.release_workflow refresh \
  --history --repetitions 15 --rounds 7 --append-samples
```

`--repetitions` and `--rounds` override the campaign timing controls for that execution. `--append-samples` asks ASV to combine new raw samples with compatible existing results and recompute statistics instead of replacing those samples.

The canonical campaigns intentionally overlap at some current-release cells. When `--append-samples` is used, those shared cells can accumulate more samples than cells unique to one campaign. That is acceptable strengthening evidence but means sample counts are not uniform across the entire result database. Preserve the raw sample counts and do not imply equal precision everywhere.

Do not use `--append-samples` after changing the benchmark semantic contract, case version, workload definition, revision identity, or comparison environment. Such evidence is not automatically comparable merely because ASV can store it.

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

Do not delete `.asv/results` merely because a report was built. Preserve authoritative result history in an approved durable evidence location so later candidates can be compared and reports can be regenerated without repeating old measurements.

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

These documents are supporting evidence/guidance. Retained ASV result files remain the measurement authority.

## 14. Per-iteration checklist

For a routine new alpha/beta candidate:

1. Commit the candidate source. ASV benchmarks commits, not uncommitted working-tree edits.
2. Update `release-compare.toml` so its first revision is the accepted prior benchmark baseline.
3. Update `release-history.toml` when the new candidate should become part of maintained backward-compatible history.
4. Run `asv check` and a real `smoke` after benchmark/package integration changes.
5. Run `python -m benchmarks.release_workflow refresh`; add `--history` for review/promotion or historical evidence.
6. Use higher `--repetitions`/`--rounds` and `--append-samples` when strengthening compatible evidence rather than creating a fresh comparison basis.
7. Inspect `campaign check`; investigate any trigger or incomplete state.
8. Preview the rebuilt site, including the feregion summary and ASV Regressions page.
9. Publish only when authorized; verify the resulting external state.
10. Retain resolved plans, normalized comparison evidence, and underlying ASV result history needed for the next iteration.

A small documentation-only correction normally does not justify rerunning every large benchmark. A benchmark-contract change, hot-path implementation change, dependency-policy change, maturity promotion, or explicit evidence-strengthening exercise can justify broader campaigns. Select the least expensive campaign set that can support the claim being made.

## 15. ASV references used by this runbook

- ASV usage and result-history model: <https://asv.readthedocs.io/en/stable/using.html>
- ASV configuration reference: <https://asv.readthedocs.io/en/stable/asv.conf.json.html>
- ASV command reference, including `compare`, `publish`, `preview`, and `gh-pages`: <https://asv.readthedocs.io/en/stable/commands.html>

The project wrapper remains authoritative for `feregion` campaign semantics and the release gate. These ASV references define the external tool behavior on which the wrapper relies.
