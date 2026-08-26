# Third-party notices and provenance

## ObsPy-distributed Flinn-Engdahl source data

The generated runtime files `src/feregion/data/fe_table.npy` and
`src/feregion/data/fe_names.npy` are derived from Flinn-Engdahl source data
distributed in the ObsPy repository.

Recorded upstream identity:

- project: ObsPy;
- repository: `https://github.com/obspy/obspy`;
- release tag: `1.4.2`;
- immutable commit: `a629e8c021052904b6b8d62699d03f2a3721ae63`;
- source path: `obspy/geodetics/data/`; and
- packaged region-name source: `names.asc`.

The repository does not version downloaded copies of the upstream `*.asc`
files. `tools/fetch_obspy_fe_data.py` downloads the pinned files into an ignored
local cache and verifies their recorded SHA-256 values before use.

ObsPy states that the ObsPy software is licensed under LGPL v3.0. This project
has not established that the same license statement governs the historical FE
source-table data. The source-data license status is therefore recorded as
**unresolved**. This notice does not infer a data license from the ObsPy software
license.

The `feregion` project itself is distributed under LGPL-3.0-only. See
`src/feregion/data/metadata.json` for source-file and generated-asset hashes.
