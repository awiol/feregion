"""Integration checks for generated assets distributed in the package."""

import json
from importlib.resources import files

import numpy as np

import feregion
from feregion._resources import load_packaged_assets


def test_packaged_assets_have_expected_structure_and_are_read_only() -> None:
    """Installed runtime assets use the validated compact representations."""

    table, names = load_packaged_assets()
    assert table.shape == (4, 91, 181)
    assert table.dtype == np.dtype(np.uint16)
    assert table.nbytes == 131_768
    assert names.shape == (758,)
    assert names.dtype.kind == "U"
    assert not table.flags.writeable
    assert not names.flags.writeable


def test_packaged_assets_cover_every_used_region_number() -> None:
    """Every region number used in the table has a non-empty direct name mapping."""

    table, names = load_packaged_assets()
    used = np.unique(table)
    assert int(used.min()) == 1
    assert int(used.max()) == 757
    assert np.all(names[used] != "")


def test_known_germany_reference_result() -> None:
    """ObsPy's documented Germany example remains unchanged at the public boundary."""

    assert feregion.lookup_number(12.0, 48.0) == 543
    assert feregion.lookup_region(12.0, 48.0).name == "GERMANY"


def test_known_northeastern_argentina_reference_result() -> None:
    """ObsPy's documented southwest-quadrant example remains unchanged."""

    assert feregion.lookup_number(-60.0, -30.0) == 133
    assert feregion.number_to_name(133) == "NORTHEASTERN ARGENTINA"


def test_packaged_names_follow_obspy_names_asc_coordinate_lookup_mapping() -> None:
    """Region-name conversion uses the same names table as ObsPy coordinate lookup."""

    assert feregion.number_to_name(4) == "KOMANDORSKIYE OSTROVA REGION"


def test_metadata_records_generated_asset_shapes() -> None:
    """Packaged provenance metadata identifies the generated data contract."""

    data = files("feregion").joinpath("data")
    metadata = json.loads(data.joinpath("metadata.json").read_text(encoding="utf-8"))
    assert metadata["assets"]["fe_table.npy"]["shape"] == [4, 91, 181]
    assert metadata["assets"]["fe_names.npy"]["shape"] == [758]


def test_metadata_records_pinned_commit_name_source_and_license_limit() -> None:
    """Provenance separates upstream software license from unresolved FE data license."""

    data = files("feregion").joinpath("data")
    metadata = json.loads(data.joinpath("metadata.json").read_text(encoding="utf-8"))
    source = metadata["source"]
    assert source["revision"] == "1.4.2"
    assert source["commit"] == "a629e8c021052904b6b8d62699d03f2a3721ae63"
    assert source["region_name_source"] == "names.asc"
    assert source["source_data_license_status"] == "unresolved"


def test_packaged_table_contains_754_active_regions_and_excludes_retired_ids() -> None:
    """The revised FE lookup contains 754 active IDs and three documented retired gaps."""

    table, _ = load_packaged_assets()
    used = set(map(int, np.unique(table)))
    assert len(used) == 754
    assert used.isdisjoint({172, 299, 550})


def test_packaged_asset_hashes_match_recorded_metadata() -> None:
    """Tracked runtime assets match the hashes recorded by their generator.

    This check detects accidental or unreviewed asset replacement even when the
    replacement still satisfies the structural shape and dtype checks.
    """

    import hashlib

    data = files("feregion").joinpath("data")
    metadata = json.loads(data.joinpath("metadata.json").read_text(encoding="utf-8"))
    for name in ("fe_table.npy", "fe_names.npy"):
        observed = hashlib.sha256(data.joinpath(name).read_bytes()).hexdigest()
        assert observed == metadata["assets"][name]["sha256"]
