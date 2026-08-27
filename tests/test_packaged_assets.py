"""Integration checks for generated assets distributed in the package."""

import hashlib
import json
from importlib.resources import files

import numpy as np

import feregion
from feregion._resources import load_packaged_assets


def test_packaged_assets_have_expected_structure_and_are_read_only() -> None:
    """Installed runtime assets use the compact geographical and seismic representations."""

    table, names, crosswalk, seismic_names = load_packaged_assets()
    assert table.shape == (4, 91, 181)
    assert table.dtype == np.dtype(np.uint16)
    assert names.shape == (758,)
    assert names.dtype.kind == "U"
    assert crosswalk.shape == (758,)
    assert crosswalk.dtype == np.dtype(np.uint8)
    assert crosswalk.nbytes == 758
    assert seismic_names.shape == (51,)
    assert seismic_names.dtype.kind == "U"
    assert all(not array.flags.writeable for array in (table, names, crosswalk, seismic_names))


def test_packaged_assets_cover_every_active_geographical_region_once() -> None:
    """Every active geographical ID has one non-empty name and one seismic parent."""

    table, names, crosswalk, _ = load_packaged_assets()
    used = np.unique(table)
    assert len(used) == 754
    assert set(range(1, 758)) - set(map(int, used)) == {172, 299, 550}
    assert np.all(names[used] != "")
    assert np.all(crosswalk[used] != 0)
    assert [int(crosswalk[number]) for number in (172, 299, 550)] == [0, 0, 0]


def test_packaged_seismic_assets_cover_exactly_regions_1_through_50() -> None:
    """The hierarchy represents all 50 seismic IDs and names."""

    table, _, crosswalk, seismic_names = load_packaged_assets()
    used_geographic = np.unique(table)
    np.testing.assert_array_equal(
        np.unique(crosswalk[used_geographic]), np.arange(1, 51, dtype=np.uint8)
    )
    assert np.all(seismic_names[1:] != "")


def test_known_germany_reference_result() -> None:
    """The historical geographical result remains unchanged and has seismic parent 36."""

    assert feregion.lookup_number(12.0, 48.0) == 543
    assert feregion.lookup_region(12.0, 48.0).name == "GERMANY"
    assert feregion.lookup_seismic_number(12.0, 48.0) == 36
    assert feregion.lookup_seismic_region(12.0, 48.0).name == "Northwestern Europe"


def test_packaged_names_follow_declared_sources() -> None:
    """Geographical and seismic packaged names retain their declared source spellings."""

    assert feregion.number_to_name(4) == "KOMANDORSKIYE OSTROVA REGION"
    assert feregion.seismic_number_to_name(1) == "Alaska - Aleutian Arc"


def test_metadata_schema_three_records_multiple_source_roles_and_offline_runtime() -> None:
    """Provenance separates source authorities and records network-free normal use."""

    data = files("feregion").joinpath("data")
    metadata = json.loads(data.joinpath("metadata.json").read_text(encoding="utf-8"))
    assert metadata["schema_version"] == 3
    assert metadata["scheme"]["structural_revision"] == "1995"
    assert set(metadata["sources"]) == {"obspy-fe-data", "young-1996", "isc-fe-standard"}
    obspy = metadata["sources"]["obspy-fe-data"]
    assert obspy["revision"] == "1.4.2"
    assert obspy["commit"] == "a629e8c021052904b6b8d62699d03f2a3721ae63"
    assert obspy["source_data_license_status"] == "unresolved"
    assert metadata["sources"]["isc-fe-standard"]["source_data_license_status"] == "unresolved"
    isc = metadata["sources"]["isc-fe-standard"]
    assert (
        isc["normalized_semantic_sha256"]
        == "e0bb924754f2aa2d8c1c025fc3ee5e074db90cc49d7ad8cd46e26353aa12079b"
    )
    assert metadata["runtime"] == {
        "network_required": False,
        "source_retrieval_required_for_normal_use": False,
    }


def test_metadata_records_all_generated_asset_shapes() -> None:
    """Packaged provenance identifies every runtime asset representation."""

    data = files("feregion").joinpath("data")
    metadata = json.loads(data.joinpath("metadata.json").read_text(encoding="utf-8"))
    assert metadata["assets"]["fe_table.npy"]["shape"] == [4, 91, 181]
    assert metadata["assets"]["fe_names.npy"]["shape"] == [758]
    assert metadata["assets"]["fe_seismic_by_geographic.npy"]["shape"] == [758]
    assert metadata["assets"]["fe_seismic_names.npy"]["shape"] == [51]


def test_packaged_asset_hashes_match_recorded_metadata() -> None:
    """Tracked runtime assets match the hashes recorded by their generator."""

    data = files("feregion").joinpath("data")
    metadata = json.loads(data.joinpath("metadata.json").read_text(encoding="utf-8"))
    for name in (
        "fe_table.npy",
        "fe_names.npy",
        "fe_seismic_by_geographic.npy",
        "fe_seismic_names.npy",
    ):
        observed = hashlib.sha256(data.joinpath(name).read_bytes()).hexdigest()
        assert observed == metadata["assets"][name]["sha256"]
