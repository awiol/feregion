# Benchmark operations

This guide explains how to operate the `feregion` ASV benchmark system and why each step exists. The benchmark harness is development tooling, not runtime API.

## 1. Mental model

The benchmark system has two owners:

- `feregion` owns benchmark semantics, deterministic workloads, historical compatibility adapters, campaign intent, normalized evidence, and the project-specific regression decision.
- ASV owns environment creation, historical package build/install, timing, raw samples, result history, comparison display, and static report generation.

A campaign is an operator-facing request. A result file is measurement evidence. A report is a derived view over retained results. Publishing changes external state and is a separate action.

Do not infer a performance regression from measurements made on different machines or dependency environments unless a declared comparison contract explicitly permits it.

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
| `smoke.toml` | Small `HEAD` integration run | First check after benchmark-system or packaging changes |
| `release-compare.toml` | Previous benchmark candidate versus `HEAD` on the fixed release environment | Routine bounded regression gate before a new candidate |
| `release-history.toml` | Backward-compatible history across representative package generations | Periodic/public history and adapter validation |
| `head-full.toml` | Every maintained case over the complete 1-2-5 load grid on `HEAD` | High-confidence/full-scale runs; intentionally expensive |
| `numpy-sensitivity.toml` | Selected NumPy versions on `HEAD` | NumPy support/performance investigations |
| `pandas-sensitivity.toml` | Selected pandas versions on `HEAD` | pandas adapter investigations |
| `python-supported.toml` | Supported CPython versions on `HEAD` | Interpreter sensitivity/support checks |
| `dependency-matrix.toml` | Sparse union of maintained NumPy and pandas sensitivity environments | Broader dependency check without a full Cartesian product |

`release-compare.toml` is intentionally versioned source. When a new benchmark candidate becomes the accepted comparison baseline, update its first revision to that candidate before issuing the next source candidate. Do not silently compare against whichever tag happens to be newest.

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

## 8. Backward-compatible historical benchmarking

The maintained historical campaign deliberately includes releases from different API generations:

```bash
uv run --locked --group benchmark \
  python -m benchmarks.campaign plan benchmarks/campaigns/release-history.toml

uv run --locked --group benchmark \
  python -m benchmarks.campaign run benchmarks/campaigns/release-history.toml
```

Modern benchmark definitions remain in control while ASV installs each selected historical package revision. The project adapter maps stable semantic cases to historical public interfaces. A capability that genuinely did not exist is skipped/not applicable; it must not be emulated or silently replaced by a different operation.

Historical campaigns are not expected to make every benchmark available at every revision. Missing capability and infrastructure/build failure are different states and must remain distinguishable.

## 9. Full HEAD and sensitivity campaigns

The routine release gate intentionally stops at 1,000,000 points so it remains practical to rerun on every candidate. The upper 2M–50M scaling points belong to `head-full` or a purpose-built investigation campaign.

The complete current implementation can be measured with:

```bash
uv run --locked --group benchmark \
  python -m benchmarks.campaign run benchmarks/campaigns/head-full.toml
```

This is intentionally expensive. Start with `smoke` and use `head-full` when the decision justifies the runtime and memory cost.

Dependency/interpreter campaigns are:

```bash
uv run --locked --group benchmark python -m benchmarks.campaign run benchmarks/campaigns/numpy-sensitivity.toml
uv run --locked --group benchmark python -m benchmarks.campaign run benchmarks/campaigns/pandas-sensitivity.toml
uv run --locked --group benchmark python -m benchmarks.campaign run benchmarks/campaigns/python-supported.toml
uv run --locked --group benchmark python -m benchmarks.campaign run benchmarks/campaigns/dependency-matrix.toml
```

The dependency matrix is a sparse union of the maintained NumPy and pandas sweeps. It is not a NumPy×pandas Cartesian product.

## 10. Rebuild and preview reports without rerunning measurements

Retained `.asv/results` are the measurement history. `.asv/html` is derived output. Rebuild the report from existing measurements with:

```bash
uv run --locked --group benchmark \
  python -m benchmarks.campaign report benchmarks/campaigns/release-history.toml
```

This delegates to `asv publish`; it does not run benchmarks. To verify this property, you may remove only the derived HTML and rebuild it:

```bash
rm -rf .asv/html
uv run --locked --group benchmark \
  python -m benchmarks.campaign report benchmarks/campaigns/release-history.toml
```

Preview through ASV's local HTTP server rather than opening `index.html` directly:

```bash
uv run --locked --group benchmark asv preview --config asv.conf.json
```

Inspect benchmark names, parameters, revision/tag history, environment selectors, gaps/skips, and regression views before publication.

Do not delete `.asv/results` merely because a report was built. Preserve authoritative result history in an approved durable evidence location so later candidates can be compared and reports can be regenerated without repeating old measurements.

## 11. Publish to GitHub Pages

Publishing is an external state change. Benchmark completion and report generation do not authorize or prove publication.

Prerequisites:

1. The intended benchmark results are retained and reviewed.
2. `campaign report` succeeds and `asv preview` shows the expected history.
3. The Git remote named `origin` points to the intended repository.
4. Repository GitHub Pages settings are configured to serve the `gh-pages` branch (or the project has an equivalent approved static-host workflow).
5. You have authority to update the publication branch.

Create/update the local `gh-pages` branch without pushing:

```bash
uv run --locked --group benchmark asv gh-pages --no-push --config asv.conf.json
```

ASV documents `gh-pages` as updating the `gh-pages` branch and, unless `--no-push` is used, pushing it to `origin`. Review the local publication commit before external mutation:

```bash
git log -1 --stat gh-pages
git show gh-pages:index.html >/dev/null
```

Then publish explicitly:

```bash
git push origin gh-pages
```

Verify the remote branch changed:

```bash
git ls-remote --heads origin gh-pages
```

Finally open the repository's configured GitHub Pages URL and verify that the expected latest revision/tag and benchmark graphs are visible. Record the observed URL/commit/time when publication status matters to a delivery or release claim.

Do not use `asv gh-pages` as a substitute for preserving `.asv/results`: the published site is a derived presentation, not the complete measurement evidence.

## 12. Per-iteration checklist

For a routine new alpha/beta candidate:

1. Commit the candidate source. ASV benchmarks commits, not uncommitted working-tree edits.
2. Update `release-compare.toml` so its first revision is the accepted prior benchmark baseline.
3. Run `plan` for `smoke` and `release-compare`.
4. Run `smoke`.
5. Run `release-compare`.
6. Run project `check`; investigate any trigger or incomplete state.
7. Run `head-full` when benchmark semantics, lookup performance, or promotion confidence requires the full scale/case surface.
8. Run dependency/Python campaigns when dependency support, interpreter support, or a performance hypothesis requires them.
9. Rebuild the public report from retained results.
10. Preview and review the report.
11. Publish only when authorized; verify the resulting external state.
12. Retain the resolved campaign plan, normalized comparison evidence, and underlying ASV result history needed for the next iteration.

A small documentation-only correction normally does not justify rerunning every large benchmark. A benchmark-contract change, hot-path implementation change, dependency-policy change, or maturity promotion can justify broader campaigns. Select the least expensive campaign set that can support the claim being made.

## 13. ASV references used by this runbook

- ASV usage and result-history model: <https://asv.readthedocs.io/en/stable/using.html>
- ASV configuration reference: <https://asv.readthedocs.io/en/stable/asv.conf.json.html>
- ASV command reference, including `compare`, `publish`, `preview`, and `gh-pages`: <https://asv.readthedocs.io/en/stable/commands.html>

The project wrapper remains authoritative for `feregion` campaign semantics and the release gate. These ASV references define the external tool behavior on which the wrapper relies.
