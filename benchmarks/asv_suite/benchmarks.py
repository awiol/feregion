"""ASV bindings for project-owned feregion benchmark cases."""

from __future__ import annotations

from typing import ClassVar

import numpy as np

from .adapters import CapabilityUnavailable, PackageAdapter
from .contracts import CASES, STANDARD_LOAD_SIZES
from .workloads import assert_region_numbers, coordinates


def _skip(exc: CapabilityUnavailable) -> None:
    """Translate a known historical capability absence to ASV's skip convention."""

    raise NotImplementedError(str(exc)) from exc


class _BatchBase:
    params: ClassVar[list[int]] = list(STANDARD_LOAD_SIZES)
    param_names: ClassVar[list[str]] = ["size"]
    number = 1
    repeat = 5
    rounds = 3
    warmup_time = 0.1

    def setup(self, size: int) -> None:
        self.adapter = PackageAdapter.installed()
        self.coordinates = coordinates(size)


class TimeGeographicLookupNumbers(_BatchBase):
    pretty_name = "Geographic batch lookup → numbers"
    pretty_source = (
        "Generate deterministic longitude/latitude coordinates; time feregion geographic "
        "batch number lookup only."
    )
    benchmark_name = "lookup_geographic_numbers"
    version = CASES[benchmark_name].semantic_version_hash

    def setup(self, size: int) -> None:
        super().setup(size)
        result = self.adapter.lookup_geographic_numbers(self.coordinates)
        assert_region_numbers(result, size=size)

    def time_lookup_geographic_numbers(self, size: int) -> None:
        self.adapter.lookup_geographic_numbers(self.coordinates)


class TimeGeographicNames(_BatchBase):
    pretty_name = "Geographic number batch → names"
    pretty_source = (
        "Prepare geographic region numbers outside timing; time batch conversion from "
        "geographic numbers to packaged names."
    )
    benchmark_name = "geographic_numbers_to_names"
    version = CASES[benchmark_name].semantic_version_hash

    def setup(self, size: int) -> None:
        super().setup(size)
        self.numbers = self.adapter.lookup_geographic_numbers(self.coordinates)
        result = self.adapter.geographic_numbers_to_names(self.numbers)
        if np.asarray(result).shape != (size,):
            raise AssertionError("name conversion changed result shape")

    def time_geographic_numbers_to_names(self, size: int) -> None:
        self.adapter.geographic_numbers_to_names(self.numbers)


class TimeSeismicLookupNumbers(_BatchBase):
    pretty_name = "Seismic batch lookup → numbers"
    pretty_source = (
        "Generate deterministic longitude/latitude coordinates; time feregion seismic batch "
        "number lookup only."
    )
    benchmark_name = "lookup_seismic_numbers"
    version = CASES[benchmark_name].semantic_version_hash

    def setup(self, size: int) -> None:
        super().setup(size)
        try:
            result = self.adapter.lookup_seismic_numbers(self.coordinates)
        except CapabilityUnavailable as exc:
            _skip(exc)
        assert_region_numbers(result, size=size, maximum=50)

    def time_lookup_seismic_numbers(self, size: int) -> None:
        self.adapter.lookup_seismic_numbers(self.coordinates)


class TimeGeographicToSeismic(_BatchBase):
    pretty_name = "Geographic numbers → seismic numbers"
    pretty_source = (
        "Prepare geographic region numbers outside timing; time batch conversion to seismic "
        "region numbers."
    )
    benchmark_name = "geographic_numbers_to_seismic_numbers"
    version = CASES[benchmark_name].semantic_version_hash

    def setup(self, size: int) -> None:
        super().setup(size)
        self.numbers = self.adapter.lookup_geographic_numbers(self.coordinates)
        try:
            result = self.adapter.geographic_numbers_to_seismic_numbers(self.numbers)
        except CapabilityUnavailable as exc:
            _skip(exc)
        assert_region_numbers(result, size=size, maximum=50)

    def time_geographic_numbers_to_seismic_numbers(self, size: int) -> None:
        self.adapter.geographic_numbers_to_seismic_numbers(self.numbers)


class _ScalarBase:
    number = 1
    repeat = 7
    rounds = 5
    warmup_time = 0.1

    def setup(self) -> None:
        self.adapter = PackageAdapter.installed()
        self.lon = 12.34
        self.lat = 56.78


class TimeGeographicScalarNumber(_ScalarBase):
    pretty_name = "Geographic scalar lookup → number"
    pretty_source = "Time one scalar longitude/latitude geographic region-number lookup."
    benchmark_name = "lookup_geographic_number"
    version = CASES[benchmark_name].semantic_version_hash

    def setup(self) -> None:
        super().setup()
        value = self.adapter.lookup_geographic_number(self.lon, self.lat)
        if not 1 <= value <= 757:
            raise AssertionError("invalid geographical number")

    def time_lookup_geographic_number(self) -> None:
        self.adapter.lookup_geographic_number(self.lon, self.lat)


class TimeGeographicScalarRegion(_ScalarBase):
    pretty_name = "Geographic scalar lookup → region"
    pretty_source = "Time one scalar longitude/latitude geographic Region lookup."
    benchmark_name = "lookup_geographic_region"
    version = CASES[benchmark_name].semantic_version_hash

    def setup(self) -> None:
        super().setup()
        self.adapter.lookup_geographic_region(self.lon, self.lat)

    def time_lookup_geographic_region(self) -> None:
        self.adapter.lookup_geographic_region(self.lon, self.lat)


class TimeGeographicScalarName(_ScalarBase):
    pretty_name = "Geographic scalar number → name"
    pretty_source = "Prepare one geographic number outside timing; time packaged-name conversion."
    benchmark_name = "geographic_number_to_name"
    version = CASES[benchmark_name].semantic_version_hash

    def setup(self) -> None:
        super().setup()
        self.number_value = self.adapter.lookup_geographic_number(self.lon, self.lat)
        if not self.adapter.geographic_number_to_name(self.number_value):
            raise AssertionError("empty geographical name")

    def time_geographic_number_to_name(self) -> None:
        self.adapter.geographic_number_to_name(self.number_value)


class TimeSeismicScalarNumber(_ScalarBase):
    pretty_name = "Seismic scalar lookup → number"
    pretty_source = "Time one scalar longitude/latitude seismic region-number lookup."
    benchmark_name = "lookup_seismic_number"
    version = CASES[benchmark_name].semantic_version_hash

    def setup(self) -> None:
        super().setup()
        try:
            value = self.adapter.lookup_seismic_number(self.lon, self.lat)
        except CapabilityUnavailable as exc:
            _skip(exc)
        if not 1 <= value <= 50:
            raise AssertionError("invalid seismic number")

    def time_lookup_seismic_number(self) -> None:
        self.adapter.lookup_seismic_number(self.lon, self.lat)


class TimeSeismicScalarRegion(_ScalarBase):
    pretty_name = "Seismic scalar lookup → region"
    pretty_source = "Time one scalar longitude/latitude seismic Region lookup."
    benchmark_name = "lookup_seismic_region"
    version = CASES[benchmark_name].semantic_version_hash

    def setup(self) -> None:
        super().setup()
        try:
            self.adapter.lookup_seismic_region(self.lon, self.lat)
        except CapabilityUnavailable as exc:
            _skip(exc)

    def time_lookup_seismic_region(self) -> None:
        self.adapter.lookup_seismic_region(self.lon, self.lat)


class _PandasBase(_BatchBase):
    def setup_frame(self, size: int) -> None:
        super().setup(size)
        try:
            import pandas as pd
        except ImportError:
            _skip(CapabilityUnavailable("pandas is unavailable in benchmark environment"))
        self.frame = pd.DataFrame(
            {"longitude": self.coordinates[:, 0], "latitude": self.coordinates[:, 1]}
        )


class TimePandasLookupNumbers(_PandasBase):
    pretty_name = "pandas lookup → geographic numbers"
    pretty_source = (
        "Prepare a DataFrame outside timing; time pandas lookup with geographic numbers only."
    )
    benchmark_name = "pandas_lookup_numbers"
    version = CASES[benchmark_name].semantic_version_hash

    def setup(self, size: int) -> None:
        self.setup_frame(size)
        try:
            result = self.adapter.pandas_lookup(self.frame, include_names=False)
        except CapabilityUnavailable as exc:
            _skip(exc)
        if len(result) != size:
            raise AssertionError("pandas adapter changed row count")

    def time_pandas_lookup_numbers(self, size: int) -> None:
        self.adapter.pandas_lookup(self.frame, include_names=False)


class TimePandasLookupNumbersAndNames(_PandasBase):
    pretty_name = "pandas lookup → numbers + names"
    pretty_source = (
        "Prepare a DataFrame outside timing; time pandas lookup with geographic numbers and "
        "packaged names."
    )
    benchmark_name = "pandas_lookup_numbers_and_names"
    version = CASES[benchmark_name].semantic_version_hash

    def setup(self, size: int) -> None:
        self.setup_frame(size)
        try:
            result = self.adapter.pandas_lookup(self.frame, include_names=True)
        except CapabilityUnavailable as exc:
            _skip(exc)
        if len(result) != size:
            raise AssertionError("pandas adapter changed row count")

    def time_pandas_lookup_numbers_and_names(self, size: int) -> None:
        self.adapter.pandas_lookup(self.frame, include_names=True)
