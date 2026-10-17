# Choose between ObsPy Flinn-Engdahl lookup and feregion

## Short answer

Use **ObsPy directly** when ObsPy is already an application dependency and the need is
an occasional scalar Flinn-Engdahl geographical-region lookup. Use **feregion** when FE
lookup should remain a small standalone dependency, when vectorized batch or pandas/CSV
processing matters, when geographical and seismic FE levels are both needed, or when
GeoJSON and explicit hierarchy-conversion interfaces are useful.

Both choices are offline for normal local FE lookup. `feregion` ships generated lookup
data derived from the pinned ObsPy 1.4.2 FE source tables and verifies its geographical
behavior against the maintained reference contract. ObsPy is therefore both an upstream
source/reference and a valid direct implementation choice. This document does not claim
that one package supersedes the other.

For `feregion` API-selection and edge-case guidance, see `user-guide.md`.

## Capability comparison

| Need | ObsPy `FlinnEngdahl` | feregion |
|---|---|---|
| Already using the wider ObsPy seismology stack | Natural choice | Additional dependency |
| One longitude/latitude → FE geographical region | Yes | Yes |
| Offline normal lookup | Yes | Yes |
| Native NumPy many-coordinate API | Not the primary `FlinnEngdahl` interface | Matrix and split-vector APIs |
| pandas adapter | No dedicated FE pandas adapter | Optional adapter |
| CSV command/workflow | Individual-coordinate FE tooling exists; bulk CSV orchestration is application work | Dedicated CSV interface |
| Geographic number/name conversion APIs | Available through ObsPy FE implementation | Scalar and batch APIs |
| FE seismic-region lookup/crosswalk | Not part of the local `obspy.geodetics.flinnengdahl.FlinnEngdahl` geographical lookup contract used as this project's oracle | Yes |
| GeoJSON export | Not the role of the local FE lookup class | Optional feregion GeoJSON support |
| Minimal FE-only dependency surface | Pulls the ObsPy package | NumPy is the only mandatory third-party runtime dependency |

## Performance evidence

Performance is workload-specific. The project keeps scalar comparator evidence, batch
scaling evidence, and release-regression evidence separate rather than turning them into
one package-wide speed claim.

### Scalar lookup

The verified direct ObsPy ASV reference campaign used CPython 3.12, NumPy 1.26.4, pandas 2.1.4,
ObsPy 1.4.2, and Setuptools 81.0.0 on the Ryzen 5 3600 benchmark host. Median scalar
geographical-number timings were about 4.680 µs for
`feregion.lookup_geographic_number()` and 3.000 µs for ObsPy
`FlinnEngdahl.get_number()`. ObsPy was therefore about `1.56x` faster for that measured
scalar operation.

That scalar observation is not a batch-performance ordering. Historical predecessor
comparator results are retained separately for provenance; current user guidance relies on
the verified reference campaign and the maintained current-release evidence below.

### feregion batch lookup

The maintained `0.6.0a5` full campaign measured the package across 12 benchmark cases
and loads through 50 million points. Numeric geographical and seismic batch paths retain
finite measurements through the largest maintained loads on the measured host. One
50-million-point seismic-name parameter exceeded ASV's initial 60-second campaign
timeout; the same parameter completed when rerun with a 180-second timeout under the
same repetition/round contract. See `benchmark-results.md` for exact observations and
resource/reporting limits.

When longitude and latitude already exist as separate arrays, `feregion` also provides
the public split-vector API. Retained exact-`0.6.0a5` direct measurements at 5 million
points found median matrix/split ratios of about `1.35x` for geographical lookup and
`1.33x` for seismic lookup; including caller `column_stack` in the geographical path
produced about `1.58x`. The matrix itself was constructed outside the matrix timing, so
this is not a comparison that unfairly charges matrix lookup for reusable input creation.
The supported guidance is to use the representation already present in the application,
not to convert between representations merely to chase a benchmark ratio.

### Release-regression evidence

The maintained 2026-10-17 comparison measured exact `v0.5.0b6` against exact
`v0.6.0a5` on the same Ryzen 5 3600 host with CPython 3.12.9, NumPy 1.26.4,
pandas 2.1.4, ASV 0.6.6, five repetitions, and three rounds. Across the maintained
10k–1M grid, candidate throughput changed between `-1.34%` and `+1.78%`; the project
regression check did not trigger. A ten-round follow-up found small same-host slowdowns
of about `2.89%` at 200k and `2.94%` at 1M, still far below the project's release
trigger. An extended comparison through 10M also did not trigger the gate.

These measurements establish bounded behavior on the stated host/environment. They do
not prove that either package is universally faster on another machine, dependency set,
or workload.

## Decision examples

Choose ObsPy directly when an event-processing application already imports ObsPy, needs
one or a few FE geographical names per event, and has no need for batch arrays,
pandas/CSV integration, seismic-region conversion, or GeoJSON. Reusing the existing
dependency usually reduces application complexity.

Choose feregion when a catalogue or DataFrame contains hundreds of thousands to millions
of coordinates, when FE lookup is used outside the rest of ObsPy, when both geographical
and seismic FE levels are required, or when a stable NumPy/pandas/CSV interface is
valuable. `feregion` provides both `(n, 2)` matrix and separate-vector batch forms so the
application can keep its natural data representation.

If an application already uses ObsPy but also has a high-volume FE preprocessing stage,
measure that application's real workload. The packages are not mutually exclusive:
ObsPy can remain the seismology framework while `feregion` handles a specialized bulk FE
transformation when that separation is justified by evidence.

## Reference basis

- ObsPy local FE implementation: `obspy.geodetics.flinnengdahl.FlinnEngdahl`.
- ObsPy itself uses `FlinnEngdahl.get_region(longitude, latitude)` when deriving FE
  descriptions in event processing.
- feregion source-data/reference provenance is recorded in
  `src/feregion/data/metadata.json` and `THIRD_PARTY_NOTICES.md`.
- Current project benchmark observations are recorded in `benchmark-results.md`.
- Benchmark migration/comparator parity is recorded in `benchmark-migration-parity.md`.

External references retained by the project:

- <https://docs.obspy.org/master/_modules/obspy/io/ndk/core.html>
- <https://docs.obspy.org/archive/1.3.1/packages/index.html>
