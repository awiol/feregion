# Choose between ObsPy Flinn-Engdahl lookup and feregion

## Short answer

Use **ObsPy directly** when ObsPy is already an application dependency and the
need is an occasional scalar Flinn-Engdahl geographical-region lookup. Use
**feregion** when Flinn-Engdahl lookup is a standalone dependency, when batch or
pandas/CSV processing matters, when geographical and seismic region levels are
both needed, or when the additional feregion interfaces and benchmarked batch
behavior justify a dedicated package.

Both choices are offline for normal local Flinn-Engdahl lookup. `feregion` uses
packaged generated data derived from the pinned ObsPy 1.4.2 Flinn-Engdahl source
tables and verifies its geographical behavior against the maintained reference
contract. ObsPy is therefore both an upstream source/reference and a valid
direct implementation choice; this document is not a claim that one package
supersedes the other.

## Capability comparison

| Need | ObsPy `FlinnEngdahl` | feregion |
|---|---|---|
| Already using the wider ObsPy seismology stack | Natural choice | Additional dependency |
| One longitude/latitude → FE geographical region | Yes | Yes |
| Offline normal lookup | Yes | Yes |
| Native NumPy many-coordinate API | Not the primary `FlinnEngdahl` interface | Yes |
| pandas adapter | No dedicated FE pandas adapter | Optional adapter |
| CSV command/workflow | ObsPy has an FE command for individual coordinate lookup; bulk CSV orchestration is application work | Dedicated CSV interface |
| Geographic number/name conversion APIs | Available through ObsPy FE implementation | Yes, scalar and batch |
| FE seismic-region lookup/crosswalk | Not part of the local `obspy.geodetics.flinnengdahl.FlinnEngdahl` geographical lookup contract used as this project's oracle | Yes |
| GeoJSON export | Not the role of the local FE lookup class | Optional feregion GeoJSON support |
| Minimal FE-only dependency surface | Pulls the ObsPy package | NumPy is the only mandatory third-party runtime dependency |

## Performance evidence

The retained b1 ASV evidence demonstrates current vectorized geographic and seismic
batch scaling through tens of millions of points on the measured Ryzen 5 3600 host.
See `benchmark-results.md` for exact timings, campaign status, and limitations.

The repository also retains a direct ObsPy comparator in the authoritative predecessor
standalone/pytest-benchmark harness. A historical predecessor result for `feregion
0.3.0a1` measured the 10,000-call scalar loop at about 357.9k feregion lookups/s versus
507.1k ObsPy lookups/s on the same host. That historical scalar result does not imply a
batch-performance ordering.

The b1 ASV `reference-comparison` campaign did execute, but its direct ObsPy result is
not valid comparative evidence. Environment investigation found that ASV requested
ObsPy 1.4.2 / NumPy 1.26.4 / pandas 2.1.4, while the actual interpreter contained
NumPy 2.5.3 and Setuptools 84.0.0; ObsPy 1.4.2 then failed to import because
`pkg_resources` was unavailable. b2 adds environment-integrity preflight and repairs the
reference profile. Until that corrected campaign is rerun, this document does not quote
a **current** feregion-versus-ObsPy speed ratio.

Do not choose feregion solely because of an unsupported speed claim. Choose it for
its dedicated interfaces and measured batch behavior; use direct comparator evidence
for the target machine/workload when relative ObsPy performance is decision-relevant.

## Decision examples

Choose ObsPy directly when an event-processing application already imports
ObsPy, needs one or a few FE geographical names per event, and has no need for
batch arrays, pandas/CSV integration, seismic-region conversion, or GeoJSON.
Keeping the existing dependency usually reduces application complexity.

Choose feregion when a catalogue or dataframe contains hundreds of thousands to
millions of coordinates, when FE lookup is used outside the rest of ObsPy, when
both geographical and seismic FE levels are required, or when a stable
NumPy/pandas/CSV interface is valuable. The benchmark evidence shows the batch
path is designed and measured for those large workloads.

If an application already uses ObsPy but also has a high-volume FE preprocessing
stage, measure that application's real workload. The packages are not mutually
exclusive: ObsPy can remain the seismology framework while feregion handles the
specialized bulk FE transformation if that separation is justified by evidence.

## Reference basis

- ObsPy local FE implementation: `obspy.geodetics.flinnengdahl.FlinnEngdahl`.
- ObsPy itself uses `FlinnEngdahl.get_region(longitude, latitude)` when deriving
  FE descriptions in event processing.
- feregion source-data/reference provenance is recorded in
  `src/feregion/data/metadata.json` and `THIRD_PARTY_NOTICES.md`.
- Current project benchmark observations are recorded in
  `docs/benchmark-results.md`.
- Benchmark migration/comparator parity is recorded in
  `docs/benchmark-migration-parity.md`.

External references:

- <https://docs.obspy.org/master/_modules/obspy/io/ndk/core.html>
- <https://docs.obspy.org/archive/1.3.1/packages/index.html>
