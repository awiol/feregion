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


## Flinn-Engdahl 1995 seismic-region hierarchy

The generated runtime files `src/feregion/data/fe_seismic_by_geographic.npy`
and `src/feregion/data/fe_seismic_names.npy` represent the 1995 FE hierarchy.
The project records Young et al. (1996), *The Flinn-Engdahl Regionalisation
Scheme: the 1995 revision*, DOI `10.1016/0031-9201(96)03141-X`, as the normative
structural-revision source. The operational geographical-to-seismic membership
and packaged seismic-name representation are obtained from the ISC Flinn-Engdahl
standards page at `https://www.isc.ac.uk/standards/FEregions/`.

`tools/fetch_isc_fe_regions.py` retrieves that page for maintainer regeneration,
normalizes its 50 seismic regions and 754 active geographical memberships, and
verifies a semantic SHA-256 before `tools/build_assets.py` creates the packaged
runtime arrays. Downloaded source material is not required for normal installed
use.

No explicit ISC/FE data redistribution license has been established by this
project. The hierarchy/name source-data license status is therefore recorded as
**unresolved**. The project LGPL-3.0-only software license is not represented as
a license grant for these upstream scientific data.
