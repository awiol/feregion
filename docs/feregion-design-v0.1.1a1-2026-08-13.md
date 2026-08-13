# feregion design

| Field | Value |
|---|---|
| Design document version | `0.1.1a1` |
| Behavioral contract series | `0.1` |
| Implementation target | `0.1.1a1` |
| Document date | `2026-08-13` |
| Canonical filename | `feregion-design-v0.1.1a1-2026-08-13.md` |
| Status | Implemented alpha design |

## 1. Design result

The runtime uses a dense table with shape `(4, 91, 181)`. Its dimensions are
quadrant, absolute integer latitude, and absolute integer longitude. The table
contains `uint16` FE region numbers. A lookup converts validated coordinates to
`uint8` latitude, longitude, and quadrant indices and performs direct table
indexing.

The batch path replaces the reference implementation's per-point Python scan
with vectorized indexing. The scalar path validates two values directly and
uses the same dense table without constructing a one-row NumPy array.

## 2. Data lifecycle and process cache

The repository does not version downloaded ObsPy FE source tables.
`tools/fetch_obspy_fe_data.py` fetches the tables for pinned ObsPy revision
`1.4.2` into `.cache/feregion/obspy-fe-1.4.2/` and verifies their expected
SHA-256 digests. `tools/build_assets.py` accepts only a verified source set and
generates:

- `fe_table.npy`: `uint16[4, 91, 181]`;
- `fe_names.npy`: one-based Unicode names; and
- `metadata.json`: source and generated-file hashes.

The generated `.npy` assets remain version-controlled and are included in the
package because normal lookup requires them. The downloaded `*.asc` inputs stay
in the ignored local cache. The installed package performs no network access,
and ObsPy is not required at runtime.

The default resource path uses two single-flight caches:

1. `load_packaged_assets()` protects first loading with a process-local lock.
   One caller reads and validates the two `.npy` files. Concurrent callers wait
   and then receive the same read-only arrays.
2. `get_default_lookup()` protects default-engine construction with a second
   process-local lock. One caller constructs the engine. Concurrent and later
   callers receive the same instance.

The fast path checks the cached reference before taking the lock, so steady-state
lookups do not acquire a cache lock. Explicit `FlinnEngdahlLookup` construction
remains available for tests and controlled alternate data.

## 3. Coordinate validation and dtype handling

Shape and dtype are validated before numeric conversion. String, object,
Boolean, and complex coordinate arrays are rejected rather than coerced.

For a supported numeric array, finiteness and coordinate range are validated in
the source dtype. Only a valid array is then converted or viewed as `float64`
for the vectorized lookup kernel. This ordering prevents a finite wider floating
value from becoming infinity during narrowing and changing the public exception
from `CoordinateRangeError` to `CoordinateValueError`.

Scalar validation follows the same rule. Python floats and NumPy floating
scalars no wider than `float64` use `math.isfinite()` because conversion to
Python float cannot narrow them. Wider NumPy floating scalars use `np.isfinite()`
in their original dtype.

After validation, the existing vectorized dense-table kernel is unchanged. The
possible removal of its `np.where()` longitude-normalization temporary remains a
measurement-driven optimization, not part of this defect-correction iteration.

## 4. Public boundaries

The core module owns scalar and array coordinate semantics. Region names remain
separate from vectorized number lookup so string allocation does not enter the
numeric hot path.

The pandas adapter and CSV command treat output columns as additive schema.
They do not provide implicit overwrite behavior:

- output columns cannot replace longitude or latitude columns;
- output columns cannot replace unrelated existing input fields; and
- when names are enabled, number and name output columns must differ.

The pandas adapter validates this schema before copying or mutating the input
DataFrame. Invalid schema raises `DataFrameColumnError`.

## 5. CSV file-safety design

CSV input remains chunked and uses the vectorized core lookup.

Filesystem output is transactional:

1. Reject input/output path aliasing before opening the destination.
2. Open the input.
3. Create a temporary file in the requested destination directory.
4. Validate the CSV header and output schema.
5. Process all chunks into the temporary file.
6. Close the temporary file.
7. Atomically replace the requested destination with `os.replace()`.
8. Remove the temporary file on any ordinary failure before replacement.

The temporary file is a sibling of the destination so replacement stays on the
same filesystem. A malformed header, invalid row, range error, or later-chunk
failure therefore does not truncate or publish a partial filesystem output.

stdout is intentionally different. It is a caller-owned stream and cannot be
rolled back. The command validates the header and schema before writing its
header, but a late row failure can leave earlier rows visible on stdout. The
process still returns status 2 and emits the error diagnostic to stderr.

CSV output-schema violations raise `CsvInputError` and are handled through the
normal CLI error boundary.

## 6. GeoJSON derivation

The FE lookup contract is one-degree based. The current scheme has 754 active
geographical regions. Region numbers 172, 299, and 550 are retired and do not
appear in the lookup tables, so the utility does not fabricate geometry for
them.

The GeoJSON utility samples all `360 * 180` one-degree cell centers, resolves
their FE numbers, run-length merges equal horizontal cells, and dissolves those
rectangles by region. Dateline-separated geometry can remain a MultiPolygon.
The feature metadata states that the result is lookup-equivalent derived
geometry.

## 7. Benchmark design

Routine benchmarks cover only in-process lookup behavior. CLI and GeoJSON are
excluded because process/I/O and geometry costs dominate those paths.

The standalone report records:

- platform, Python, NumPy, and feregion versions;
- deterministic workload seed and coordinate distribution;
- warmup and repeated wall-clock timings;
- candidate correctness checks before timing;
- scalar candidate/reference measurements;
- vectorized candidate throughput at representative sizes;
- a direct batch comparison that times the candidate and verified source-table
  breakpoint scan on the **same coordinates** for 100, 1,000, 10,000, and
  100,000 points; and
- median candidate speedup for each direct comparison workload.

The `pytest-benchmark` harness also contains candidate and verified-source
batch cases on the same bounded workload family. ObsPy remains an optional
additional reference when installed.

Benchmark results are environment-specific evidence, not throughput SLAs.
Scalar performance remains a review signal and does not justify complexity in
the batch hot path without measured benefit.

## 8. Quality considerations

### Behavioral correctness

The design preserves the reference `-180 -> +180` rule, sign-based quadrants,
and integer truncation after absolute value. Tests cover each quadrant,
coordinate limits, extended floating validation, output-schema collisions,
transactional CSV failure, and synchronized concurrent initialization.
When the verified source cache is present, generated assets are compared with an
independent source-table reference.

### Compatibility

The region-mapping API and dense-table semantics remain compatible with the
0.1 alpha series. CSV and pandas behavior is intentionally stricter where prior
behavior could overwrite caller data. Such collisions now fail explicitly
instead of silently replacing data.

### Performance and resources

The batch hot path still has no Python loop over points. The dense numeric table
uses 131,768 bytes. Single-flight locks affect only first initialization;
steady-state cache hits return without lock acquisition. File-safe CSV output
adds one temporary sibling and one atomic replacement for filesystem outputs.

### Maintainability and testability

The generated-data boundary isolates upstream acquisition and source parsing
from runtime lookup. The fetch tool owns network access and digest verification.
The asset builder owns source parsing and deterministic generation. The engine
can be constructed with synthetic arrays. Cache-reset helpers are private and
exist only to make first-use concurrency tests deterministic. Filesystem output
transaction logic is isolated from CSV row processing.

### Security and robustness

NumPy assets load with `allow_pickle=False`. The runtime has no network access.
Transactional file output prevents known destructive alias/truncation failure
modes. Output schema validation prevents silent loss of existing fields.

### Knowledge and provenance

Requirements, design rationale, source-acquisition and generation tooling,
metadata, license notices, generated runtime assets, tests, and benchmark
harnesses version with the source. Downloaded upstream tables do not. Generated
benchmark results, verification logs, and per-iteration review reports stay
outside the repository source tree.

## 9. Repository and delivery structure

The source archive has a versioned outer filename and a stable internal
`feregion/` root.

Requirements and design are intentional versioned/date-stamped repository
artifacts for this project. The 0.1.1a1 paths are:

- `docs/feregion-requirements-v0.1.1a1-2026-08-13.md`;
- `docs/feregion-design-v0.1.1a1-2026-08-13.md`.

A later iteration renames these two files and updates repository references in
the same change. Superseded requirements and design filenames are removed so
the repository contains only the current contract. `docs/testing.md` remains a
stable maintainer guide.

The repository uses `uv` directly for environment management, command
execution, and distribution builds. `pyproject.toml` owns dependency groups and
tool configuration. A Makefile is not used because it would duplicate short
`uv` commands and create a second maintenance surface. The published `test`,
`dev`, and `benchmark` extras remain compatibility installation routes for this
patch release, but dependency groups define the canonical repository workflow.

Delivery manifests, checksum lists, benchmark-result reports, verification
records, and review reports remain outside the source repository. The delivery
manifest binds those sidecars to the exact source archive and patch.

## 10. Delivery verification

For an iterative delivery with an exact prior source archive:

1. build the target source archive from an isolated staging tree;
2. generate a binary-capable Git patch from the exact prior delivered source;
3. apply the patch to a clean baseline;
4. compare reconstructed and target source files byte-for-byte;
5. run focused and broader tests plus packaging checks;
6. execute the standalone benchmark and retain the direct comparison table;
7. scan source and archive structure for unintended transient/private content;
8. calculate final SHA-256 values after artifacts stop changing; and
9. record review, approval, and verification states separately in the delivery
   manifest.

## 11. Deferred decisions

A Rust backend is deferred. If benchmark evidence later shows a material gap,
any Rust implementation must pass the same behavioral contract suite before it
can become a supported backend.

A more compact or memory-mapped asset format is also deferred. The current
numeric table is small enough that format complexity has no demonstrated
benefit.

A repository `uv.lock` is also deferred in this delivery because the execution
environment cannot resolve all development packages from the package index.
The file is not ignored. When maintainers generate a lock in a network-enabled
environment, it can be committed as repository metadata.

The vectorized `np.where()` normalization temporary is also deferred. It should
change only after controlled time and peak-memory measurements demonstrate a
material benefit without reducing correctness or clarity.
