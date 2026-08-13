"""Top-level convenience functions preserve the default engine contract."""

import numpy as np

import feregion


def test_top_level_lookup_numbers_uses_default_engine() -> None:
    """The public vector convenience function exposes the cached lookup result."""

    result = feregion.lookup_numbers(np.array([[12.0, 48.0], [-60.0, -30.0]]))
    assert result.tolist() == [543, 133]


def test_top_level_numbers_to_names_uses_default_engine() -> None:
    """The public vector name converter preserves shape and canonical names."""

    result = feregion.numbers_to_names(np.array([[543, 133]], dtype=np.uint16))
    assert result.tolist() == [["GERMANY", "NORTHEASTERN ARGENTINA"]]
