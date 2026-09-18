# Observed benchmark results

## Purpose and evidence status

This document records benchmark observations available during the final `0.4`
alpha review preparation on 2026-09-18. It is an **observational snapshot**, not
a universal performance guarantee and not a substitute for retained ASV result
files. Re-run the maintained campaigns before making a release-specific claim.

The source evidence was the populated ASV 0.6.6 result/report archive supplied by
the maintainer on 2026-09-18, SHA-256
`5157a6ea65e269e46e8a494e005482e383368fbec7f1a18a3c62411746dcbab6`.
The current measured candidate in that snapshot was Git commit
`226b36441a3d604b4b7b26536ffbff3c88e17bca` (`v0.4.0a7`). The principal
machine identity was:

- machine: `awiol-ryzen3600`;
- CPU: AMD Ryzen 5 3600 6-Core Processor, 12 logical CPUs;
- RAM: 32 GB;
- OS: Linux 6.8.0-138-generic.

Unless stated otherwise, ratios below are geometric means of directly comparable
measurements. A ratio below `1.0` is faster than the named baseline; above `1.0`
is slower. These aggregate ratios are diagnostic summaries, not project release
gates. The project gate remains the requirement in `REQ-PERF-006`.

## Current batch scale

On `0.4.0a7`, CPython 3.12, NumPy 1.26.4, and pandas 2.1.4, representative core
batch measurements were:

| Case | 10,000 points | 100,000 points | 1,000,000 points |
|---|---:|---:|---:|
| Geographic batch lookup | 0.165 ms | 1.256 ms | 16.705 ms |
| Seismic batch lookup | 0.178 ms | 1.427 ms | 17.924 ms |

Those measurements correspond to roughly 56–80 million coordinate lookups per
second over these three loads on the measured host. This is evidence for the
`feregion` vectorized batch path on this host; it is not a direct comparison with
ObsPy.

## Python-version sensitivity

For `0.4.0a7`, NumPy 2.3.5, pandas 2.3.3, and the geographic/seismic batch cases
at 10k, 100k, and 1M points, CPython 3.11 is the ratio baseline:

| Python | Geometric timing ratio | Observation |
|---|---:|---|
| 3.11 | 1.000 | baseline |
| 3.12 | 1.060 | about 6% slower in this snapshot |
| 3.13 | 1.164 | about 16% slower in this snapshot |
| 3.14 | 0.979 | about 2% faster in this snapshot |

This is single-host evidence. The differences, especially between adjacent
interpreter versions, should be strengthened with additional rounds before they
are treated as durable interpreter-performance characteristics.

## NumPy-version sensitivity

For `0.4.0a7`, CPython 3.12, pandas 2.1.4, and the geographic/seismic batch cases
at 10k, 100k, and 1M points:

| NumPy | Ratio vs 1.26.4 | Observation |
|---|---:|---|
| 1.26.4 | 1.000 | baseline |
| 2.0.2 | 0.991 | about 0.9% faster |
| 2.2.6 | 0.976 | about 2.4% faster |
| 2.5.2 | 0.981 | about 1.9% faster |

The newer NumPy versions are slightly favorable in this snapshot, but the
spread is small. There is no evidence here for selecting one supported NumPy
version solely for performance.

## pandas-version sensitivity

For `0.4.0a7`, CPython 3.12 and NumPy 1.26.4, pandas behavior depends strongly on
which adapter result is requested:

| pandas | Numbers-only ratio vs 2.1.4 | Numbers + names ratio vs 2.1.4 |
|---|---:|---:|
| 2.1.4 | 1.000 | 1.000 |
| 2.2.3 | 1.009 | 0.973 |
| 2.3.3 | 0.988 | 0.989 |
| 3.0.5 | 1.208 | 0.616 |

pandas 2.2.3 and 2.3.3 are comparatively balanced in this evidence. pandas
3.0.5 is not uniformly better: numbers-only lookup is about 21% slower by the
geometric summary, while numbers-plus-names is about 38% faster. At the 100k
load specifically, the numbers-only measurement was about 56% slower than
pandas 2.1.4. This divergence is an investigation target, not a basis for calling
pandas 3.0.5 globally favorable or unfavorable.

## Performance across feregion releases

The fixed historical comparison environment is CPython 3.12, NumPy 1.26.4, and
pandas 2.1.4. Each row below uses only measurements common to both adjacent
revisions; therefore row coverage differs and ratios must not be compared as if
they were one uniform score.

| Transition | Common measurements | Geometric ratio | Main observation |
|---|---:|---:|---|
| 0.1.2a10 → 0.2.0b1 | 4 | 1.483 | material early slowdown, concentrated in seismic lookup |
| 0.2.0b1 → 0.3.0b1 | 4 | 0.875 | recovery, with seismic lookup about 24% faster geometrically |
| 0.3.0b1 → 0.4.0a5 | 9 | 0.807 | broad improvement; geographic about 20% faster and seismic about 35% faster geometrically |
| 0.4.0a5 → 0.4.0a6 | 12 | 1.010 | approximately flat overall |
| 0.4.0a6 → 0.4.0a7 | 12 | 1.008 | approximately flat overall |

The last two transitions are important context for the ASV regression page:
small step-detection signals can occur even when the broad same-environment
release comparison is approximately flat.

## ASV regression signals versus the project gate

The populated ASV report contained seven regression signals using ASV's normal
step detector. The largest observed signal was about 29% for seismic lookup at
10k in one Python/dependency environment; another was about 18% for geographic
lookup at 100k. The remaining signals were smaller.

None of the observed signals satisfied the `feregion` release trigger of more
than 25% slowdown at **two adjacent maintained load sizes of at least 10,000**
under one comparable machine/environment basis. Treat the ASV regression page as
a sensitive investigation surface and `benchmarks.campaign check` as the
project release-decision surface.

## Limitations and next evidence step

The observations above come from one host and a finite number of rounds. They
support investigation and dependency/interpreter selection discussions, but do
not establish causal explanations. The recommended strengthening run is:

```bash
uv run --locked --group benchmark \
  python -m benchmarks.release_workflow refresh \
  --history --repetitions 15 --rounds 7 --append-samples
```

This appends new raw samples to compatible retained ASV results, reruns the
current full suite, sparse dependency matrix, supported-Python matrix, routine
release comparison, and historical campaign, re-applies the project release
check, and rebuilds the report. Preserve `.asv/results` before and after the run.
