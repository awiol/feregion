# Third-party notices

## ObsPy Flinn-Engdahl source data

The generated runtime files `src/feregion/data/fe_table.npy` and
`src/feregion/data/fe_names.npy` are derived from Flinn-Engdahl source data
distributed by ObsPy.

Source project: ObsPy

Source repository: `https://github.com/obspy/obspy`

Pinned source revision: `1.4.2`

Source location: `obspy/geodetics/data/`

The repository does not version downloaded copies of the upstream `*.asc`
files. `tools/fetch_obspy_fe_data.py` downloads the pinned files into an ignored
local cache and verifies the expected SHA-256 digests before use.

ObsPy states that it is licensed under LGPL v3.0. Source-file and generated-asset
SHA-256 values are recorded in `src/feregion/data/metadata.json`.

This project does not copy ObsPy's Python Flinn-Engdahl implementation into its
runtime source. ObsPy is optional development software for oracle tests and
benchmarks.
