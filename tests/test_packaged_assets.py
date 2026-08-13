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


def test_metadata_records_generated_asset_shapes() -> None:
    """Packaged provenance metadata identifies the generated data contract."""

    data = files("feregion").joinpath("data")
    metadata = json.loads(data.joinpath("metadata.json").read_text(encoding="utf-8"))
    assert metadata["assets"]["fe_table.npy"]["shape"] == [4, 91, 181]
    assert metadata["assets"]["fe_names.npy"]["shape"] == [758]


def test_packaged_table_contains_754_active_regions_and_excludes_retired_ids() -> None:
    """The revised FE lookup contains 754 active IDs and three documented retired gaps."""

    table, _ = load_packaged_assets()
    used = set(map(int, np.unique(table)))
    assert len(used) == 754
    assert used.isdisjoint({172, 299, 550})
