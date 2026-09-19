"""ASV bindings for project-owned feregion benchmark cases."""

from __future__ import annotations

from collections.abc import Callable
from typing import ClassVar

import numpy as np

from .adapters import CapabilityUnavailable, PackageAdapter
from .contracts import CASES, DIAGNOSTIC_LOAD_SIZES, REFERENCE_LOAD_SIZES, STANDARD_LOAD_SIZES
from .environment import EnvironmentIntegrityError, verify_benchmark_environment
from .source_oracle import (
    OracleUnavailable,
    geographic_to_seismic,
    seismic_names,
    source_reference,
)
from .state import record_state
from .workloads import (
    assert_crosswalk_matches_source,
    assert_geographic_names_match_source,
    assert_geographic_numbers_match_source,
    assert_region_object,
    assert_seismic_names_match_oracle,
    assert_seismic_numbers_match_source,
    coordinates,
    expected_geographic_numbers,
)


def _skip(exc: CapabilityUnavailable, *, case_id: str, load_size: int | None = None) -> None:
    """Translate capability absence to ASV skip semantics and retained state."""

    record_state(case_id, load_size, "not_applicable", reason=str(exc))
    raise NotImplementedError(str(exc)) from exc


def _require_environment(case_id: str, load_size: int | None) -> object:
    """Verify the ASV environment and retain a case-level failure on drift."""

    try:
        return verify_benchmark_environment()
    except EnvironmentIntegrityError as exc:
        record_state(case_id, load_size, "build_unavailable", reason=str(exc))
        raise


def _checked_setup(
    case_id: str,
    load_size: int | None,
    check: Callable[[], None],
) -> None:
    """Run untimed semantic checking and retain a discriminating setup outcome."""

    try:
        check()
    except OracleUnavailable as exc:
        record_state(case_id, load_size, "build_unavailable", reason=str(exc))
        raise
    except AssertionError as exc:
        record_state(case_id, load_size, "correctness_failed", reason=str(exc))
        raise
    except Exception as exc:
        record_state(case_id, load_size, "execution_failed", reason=repr(exc))
        raise
    record_state(case_id, load_size, "correctness_passed")


class _BatchBase:
    params: ClassVar[list[int]] = list(STANDARD_LOAD_SIZES)
    param_names: ClassVar[list[str]] = ["size"]
    number = 1
    repeat = 5
    rounds = 3
    warmup_time = 0.1

    def setup(self, size: int) -> None:
        _require_environment(self.benchmark_name, size)
        self.adapter = PackageAdapter.installed()
        self.coordinates = coordinates(size)


class TimeGeographicLookupNumbers(_BatchBase):
    pretty_name = "Geographic batch lookup → numbers"
    pretty_source = (
        "Generate deterministic longitude/latitude coordinates; verify a bounded sample against "
        "the pinned source-table scanner; time feregion batch number lookup only."
    )
    benchmark_name = "lookup_geographic_numbers"
    version = CASES[benchmark_name].semantic_version_hash

    def setup(self, size: int) -> None:
        super().setup(size)
        result = self.adapter.lookup_geographic_numbers(self.coordinates)
        _checked_setup(
            self.benchmark_name,
            size,
            lambda: assert_geographic_numbers_match_source(result, self.coordinates),
        )

    def time_lookup_geographic_numbers(self, size: int) -> None:
        self.adapter.lookup_geographic_numbers(self.coordinates)


class TimeGeographicNames(_BatchBase):
    pretty_name = "Geographic number batch → names"
    pretty_source = (
        "Prepare verified geographic region numbers outside timing; verify sampled names against "
        "pinned source names; time packaged-name conversion."
    )
    benchmark_name = "geographic_numbers_to_names"
    version = CASES[benchmark_name].semantic_version_hash

    def setup(self, size: int) -> None:
        super().setup(size)
        self.numbers = self.adapter.lookup_geographic_numbers(self.coordinates)
        result = self.adapter.geographic_numbers_to_names(self.numbers)

        def check() -> None:
            assert_geographic_numbers_match_source(self.numbers, self.coordinates)
            assert_geographic_names_match_source(result, self.numbers)

        _checked_setup(self.benchmark_name, size, check)

    def time_geographic_numbers_to_names(self, size: int) -> None:
        self.adapter.geographic_numbers_to_names(self.numbers)


class TimeSeismicLookupNumbers(_BatchBase):
    pretty_name = "Seismic batch lookup → numbers"
    pretty_source = (
        "Generate deterministic coordinates; verify sampled results against source geographic "
        "lookup plus the project crosswalk; time seismic batch lookup only."
    )
    benchmark_name = "lookup_seismic_numbers"
    version = CASES[benchmark_name].semantic_version_hash

    def setup(self, size: int) -> None:
        super().setup(size)
        try:
            result = self.adapter.lookup_seismic_numbers(self.coordinates)
        except CapabilityUnavailable as exc:
            _skip(exc, case_id=self.benchmark_name, load_size=size)
        _checked_setup(
            self.benchmark_name,
            size,
            lambda: assert_seismic_numbers_match_source(result, self.coordinates),
        )

    def time_lookup_seismic_numbers(self, size: int) -> None:
        self.adapter.lookup_seismic_numbers(self.coordinates)


class TimeGeographicToSeismic(_BatchBase):
    pretty_name = "Geographic numbers → seismic numbers"
    pretty_source = (
        "Prepare source-verified geographic numbers outside timing; verify sampled conversion "
        "against the project crosswalk; time hierarchy conversion."
    )
    benchmark_name = "geographic_numbers_to_seismic_numbers"
    version = CASES[benchmark_name].semantic_version_hash

    def setup(self, size: int) -> None:
        super().setup(size)
        self.numbers = self.adapter.lookup_geographic_numbers(self.coordinates)
        try:
            result = self.adapter.geographic_numbers_to_seismic_numbers(self.numbers)
        except CapabilityUnavailable as exc:
            _skip(exc, case_id=self.benchmark_name, load_size=size)

        def check() -> None:
            assert_geographic_numbers_match_source(self.numbers, self.coordinates)
            assert_crosswalk_matches_source(result, self.numbers)

        _checked_setup(self.benchmark_name, size, check)

    def time_geographic_numbers_to_seismic_numbers(self, size: int) -> None:
        self.adapter.geographic_numbers_to_seismic_numbers(self.numbers)


class TimeSeismicNames(_BatchBase):
    pretty_name = "Seismic number batch → names"
    pretty_source = (
        "Prepare source-verified seismic numbers outside timing; verify sampled names against the "
        "project seismic-name oracle; time name conversion."
    )
    benchmark_name = "seismic_numbers_to_names"
    version = CASES[benchmark_name].semantic_version_hash

    def setup(self, size: int) -> None:
        super().setup(size)
        try:
            self.numbers = self.adapter.lookup_seismic_numbers(self.coordinates)
            result = self.adapter.seismic_numbers_to_names(self.numbers)
        except CapabilityUnavailable as exc:
            _skip(exc, case_id=self.benchmark_name, load_size=size)

        def check() -> None:
            assert_seismic_numbers_match_source(self.numbers, self.coordinates)
            assert_seismic_names_match_oracle(result, self.numbers)

        _checked_setup(self.benchmark_name, size, check)

    def time_seismic_numbers_to_names(self, size: int) -> None:
        self.adapter.seismic_numbers_to_names(self.numbers)


class _ScalarBase:
    number = 1
    repeat = 7
    rounds = 5
    warmup_time = 0.1

    def setup(self) -> None:
        _require_environment(self.benchmark_name, None)
        self.adapter = PackageAdapter.installed()
        self.lon = 12.34
        self.lat = 56.78


class TimeGeographicScalarNumber(_ScalarBase):
    pretty_name = "Geographic scalar lookup → number"
    pretty_source = "Verify against the pinned source scanner; time one feregion scalar lookup."
    benchmark_name = "lookup_geographic_number"
    version = CASES[benchmark_name].semantic_version_hash

    def setup(self) -> None:
        super().setup()
        value = self.adapter.lookup_geographic_number(self.lon, self.lat)
        _checked_setup(
            self.benchmark_name,
            None,
            lambda: _assert_equal(value, source_reference().number(self.lon, self.lat)),
        )

    def time_lookup_geographic_number(self) -> None:
        self.adapter.lookup_geographic_number(self.lon, self.lat)


class TimeGeographicScalarRegion(_ScalarBase):
    pretty_name = "Geographic scalar lookup → region"
    pretty_source = "Verify number/name against pinned source tables; time Region construction."
    benchmark_name = "lookup_geographic_region"
    version = CASES[benchmark_name].semantic_version_hash

    def setup(self) -> None:
        super().setup()
        region = self.adapter.lookup_geographic_region(self.lon, self.lat)

        def check() -> None:
            oracle = source_reference()
            expected_number = oracle.number(self.lon, self.lat)
            assert_region_object(
                region,
                expected_number=expected_number,
                expected_name=oracle.name(expected_number),
            )

        _checked_setup(self.benchmark_name, None, check)

    def time_lookup_geographic_region(self) -> None:
        self.adapter.lookup_geographic_region(self.lon, self.lat)


class TimeGeographicScalarName(_ScalarBase):
    pretty_name = "Geographic scalar number → name"
    pretty_source = "Prepare a source-derived number; verify name; time packaged-name conversion."
    benchmark_name = "geographic_number_to_name"
    version = CASES[benchmark_name].semantic_version_hash

    def setup(self) -> None:
        super().setup()
        oracle = source_reference()
        self.number_value = oracle.number(self.lon, self.lat)
        result = self.adapter.geographic_number_to_name(self.number_value)
        _checked_setup(
            self.benchmark_name,
            None,
            lambda: _assert_equal(result, oracle.name(self.number_value)),
        )

    def time_geographic_number_to_name(self) -> None:
        self.adapter.geographic_number_to_name(self.number_value)


class TimeSeismicScalarNumber(_ScalarBase):
    pretty_name = "Seismic scalar lookup → number"
    pretty_source = "Verify against source lookup plus crosswalk; time one seismic scalar lookup."
    benchmark_name = "lookup_seismic_number"
    version = CASES[benchmark_name].semantic_version_hash

    def setup(self) -> None:
        super().setup()
        try:
            value = self.adapter.lookup_seismic_number(self.lon, self.lat)
        except CapabilityUnavailable as exc:
            _skip(exc, case_id=self.benchmark_name)

        def check() -> None:
            geographic = source_reference().number(self.lon, self.lat)
            _assert_equal(value, int(geographic_to_seismic()[geographic]))

        _checked_setup(self.benchmark_name, None, check)

    def time_lookup_seismic_number(self) -> None:
        self.adapter.lookup_seismic_number(self.lon, self.lat)


class TimeSeismicScalarRegion(_ScalarBase):
    pretty_name = "Seismic scalar lookup → region"
    pretty_source = (
        "Verify number/name against source-derived seismic identity; time Region lookup."
    )
    benchmark_name = "lookup_seismic_region"
    version = CASES[benchmark_name].semantic_version_hash

    def setup(self) -> None:
        super().setup()
        try:
            region = self.adapter.lookup_seismic_region(self.lon, self.lat)
        except CapabilityUnavailable as exc:
            _skip(exc, case_id=self.benchmark_name)

        def check() -> None:
            geographic = source_reference().number(self.lon, self.lat)
            expected = int(geographic_to_seismic()[geographic])
            assert_region_object(
                region,
                expected_number=expected,
                expected_name=str(seismic_names()[expected]),
            )

        _checked_setup(self.benchmark_name, None, check)

    def time_lookup_seismic_region(self) -> None:
        self.adapter.lookup_seismic_region(self.lon, self.lat)


class _PandasBase(_BatchBase):
    def setup_frame(self, size: int) -> None:
        super().setup(size)
        try:
            import pandas as pd
        except ImportError:
            _skip(
                CapabilityUnavailable("pandas is unavailable in benchmark environment"),
                case_id=self.benchmark_name,
                load_size=size,
            )
        self.frame = pd.DataFrame(
            {"longitude": self.coordinates[:, 0], "latitude": self.coordinates[:, 1]}
        )

    def _check_geographic_frame(self, result: object, *, include_names: bool) -> None:
        numbers = np.asarray(result["fe_number"])
        assert_geographic_numbers_match_source(numbers, self.coordinates)
        if include_names:
            assert_geographic_names_match_source(np.asarray(result["fe_region"]), numbers)


class TimePandasLookupNumbers(_PandasBase):
    pretty_name = "pandas lookup → geographic numbers"
    pretty_source = "Prepare a DataFrame; verify source identities; time copy-return lookup."
    benchmark_name = "pandas_lookup_numbers"
    version = CASES[benchmark_name].semantic_version_hash

    def setup(self, size: int) -> None:
        self.setup_frame(size)
        try:
            result = self.adapter.pandas_lookup(self.frame, include_names=False)
        except CapabilityUnavailable as exc:
            _skip(exc, case_id=self.benchmark_name, load_size=size)
        _checked_setup(
            self.benchmark_name,
            size,
            lambda: self._check_geographic_frame(result, include_names=False),
        )

    def time_pandas_lookup_numbers(self, size: int) -> None:
        self.adapter.pandas_lookup(self.frame, include_names=False)


class TimePandasLookupNumbersAndNames(_PandasBase):
    pretty_name = "pandas lookup → numbers + names"
    pretty_source = "Prepare a DataFrame; verify source identities/names; time copy-return lookup."
    benchmark_name = "pandas_lookup_numbers_and_names"
    version = CASES[benchmark_name].semantic_version_hash

    def setup(self, size: int) -> None:
        self.setup_frame(size)
        try:
            result = self.adapter.pandas_lookup(self.frame, include_names=True)
        except CapabilityUnavailable as exc:
            _skip(exc, case_id=self.benchmark_name, load_size=size)
        _checked_setup(
            self.benchmark_name,
            size,
            lambda: self._check_geographic_frame(result, include_names=True),
        )

    def time_pandas_lookup_numbers_and_names(self, size: int) -> None:
        self.adapter.pandas_lookup(self.frame, include_names=True)


class _PandasInplaceBase(_PandasBase):
    params: ClassVar[list[int]] = list(DIAGNOSTIC_LOAD_SIZES)


class TimePandasLookupInplaceNumbers(_PandasInplaceBase):
    pretty_name = "pandas in-place lookup → geographic numbers"
    pretty_source = (
        "Prepare a fresh DataFrame outside timing; verify source identities; time in-place lookup."
    )
    benchmark_name = "pandas_lookup_inplace_numbers"
    version = CASES[benchmark_name].semantic_version_hash

    def setup(self, size: int) -> None:
        self.setup_frame(size)
        try:
            result = self.adapter.pandas_lookup(self.frame, include_names=False, inplace=True)
        except CapabilityUnavailable as exc:
            _skip(exc, case_id=self.benchmark_name, load_size=size)
        _checked_setup(
            self.benchmark_name,
            size,
            lambda: self._check_geographic_frame(result, include_names=False),
        )
        self.setup_frame(size)

    def time_pandas_lookup_inplace_numbers(self, size: int) -> None:
        self.adapter.pandas_lookup(self.frame, include_names=False, inplace=True)


class TimePandasLookupInplaceNumbersAndNames(_PandasInplaceBase):
    pretty_name = "pandas in-place lookup → numbers + names"
    pretty_source = "Prepare a fresh DataFrame outside timing; verify names; time in-place lookup."
    benchmark_name = "pandas_lookup_inplace_numbers_and_names"
    version = CASES[benchmark_name].semantic_version_hash

    def setup(self, size: int) -> None:
        self.setup_frame(size)
        try:
            result = self.adapter.pandas_lookup(self.frame, include_names=True, inplace=True)
        except CapabilityUnavailable as exc:
            _skip(exc, case_id=self.benchmark_name, load_size=size)
        _checked_setup(
            self.benchmark_name,
            size,
            lambda: self._check_geographic_frame(result, include_names=True),
        )
        self.setup_frame(size)

    def time_pandas_lookup_inplace_numbers_and_names(self, size: int) -> None:
        self.adapter.pandas_lookup(self.frame, include_names=True, inplace=True)


class _DiagnosticBatchBase(_BatchBase):
    params: ClassVar[list[int]] = list(DIAGNOSTIC_LOAD_SIZES)


class TimePandasLookupInplaceSeismicNumbers(_PandasInplaceBase):
    pretty_name = "pandas in-place lookup → seismic numbers"
    pretty_source = (
        "Prepare a fresh DataFrame; verify source-derived seismic identities; time in-place lookup."
    )
    benchmark_name = "pandas_lookup_inplace_seismic_numbers"
    version = CASES[benchmark_name].semantic_version_hash

    def setup(self, size: int) -> None:
        self.setup_frame(size)
        try:
            result = self.adapter.pandas_lookup(
                self.frame,
                include_names=False,
                inplace=True,
                level="seismic",
            )
        except CapabilityUnavailable as exc:
            _skip(exc, case_id=self.benchmark_name, load_size=size)
        _checked_setup(
            self.benchmark_name,
            size,
            lambda: assert_seismic_numbers_match_source(
                np.asarray(result["fe_seismic_number"]),
                self.coordinates,
            ),
        )
        self.setup_frame(size)

    def time_pandas_lookup_inplace_seismic_numbers(self, size: int) -> None:
        self.adapter.pandas_lookup(
            self.frame,
            include_names=False,
            inplace=True,
            level="seismic",
        )


class TimeInternalSplitGeographic(_DiagnosticBatchBase):
    pretty_name = "Internal split-vector geographic lookup"
    pretty_source = "Diagnostic private-path timing retained for predecessor benchmark parity."
    benchmark_name = "internal_split_geographic_numbers"
    version = CASES[benchmark_name].semantic_version_hash

    def setup(self, size: int) -> None:
        super().setup(size)
        self.longitude = self.coordinates[:, 0].copy()
        self.latitude = self.coordinates[:, 1].copy()
        try:
            result = self.adapter.split_geographic_numbers(self.longitude, self.latitude)
        except CapabilityUnavailable as exc:
            _skip(exc, case_id=self.benchmark_name, load_size=size)
        _checked_setup(
            self.benchmark_name,
            size,
            lambda: assert_geographic_numbers_match_source(result, self.coordinates),
        )

    def time_internal_split_geographic_numbers(self, size: int) -> None:
        self.adapter.split_geographic_numbers(self.longitude, self.latitude)


class TimeInternalSplitSeismic(_DiagnosticBatchBase):
    pretty_name = "Internal split-vector seismic lookup"
    pretty_source = "Diagnostic private-path timing retained for predecessor benchmark parity."
    benchmark_name = "internal_split_seismic_numbers"
    version = CASES[benchmark_name].semantic_version_hash

    def setup(self, size: int) -> None:
        super().setup(size)
        self.longitude = self.coordinates[:, 0].copy()
        self.latitude = self.coordinates[:, 1].copy()
        try:
            result = self.adapter.split_seismic_numbers(self.longitude, self.latitude)
        except CapabilityUnavailable as exc:
            _skip(exc, case_id=self.benchmark_name, load_size=size)
        _checked_setup(
            self.benchmark_name,
            size,
            lambda: assert_seismic_numbers_match_source(result, self.coordinates),
        )

    def time_internal_split_seismic_numbers(self, size: int) -> None:
        self.adapter.split_seismic_numbers(self.longitude, self.latitude)


class TimeStackPlusGeographic(_DiagnosticBatchBase):
    pretty_name = "Stack vectors + geographic batch lookup"
    pretty_source = "Diagnostic timing of column_stack plus public batch lookup."
    benchmark_name = "stack_plus_geographic_numbers"
    version = CASES[benchmark_name].semantic_version_hash

    def setup(self, size: int) -> None:
        super().setup(size)
        self.longitude = self.coordinates[:, 0].copy()
        self.latitude = self.coordinates[:, 1].copy()
        result = self.adapter.lookup_geographic_numbers(
            np.column_stack((self.longitude, self.latitude))
        )
        _checked_setup(
            self.benchmark_name,
            size,
            lambda: assert_geographic_numbers_match_source(result, self.coordinates),
        )

    def time_stack_plus_geographic_numbers(self, size: int) -> None:
        self.adapter.lookup_geographic_numbers(np.column_stack((self.longitude, self.latitude)))


class TimeObsPyScalarNumber(_ScalarBase):
    pretty_name = "ObsPy scalar geographic lookup → number"
    pretty_source = (
        "Direct ObsPy FlinnEngdahl scalar comparator, verified against pinned source tables."
    )
    benchmark_name = "obspy_geographic_number"
    version = CASES[benchmark_name].semantic_version_hash

    def setup(self) -> None:
        report = _require_environment(self.benchmark_name, None)
        if "obspy" not in getattr(report, "requested", {}):
            _skip(
                CapabilityUnavailable(
                    "ObsPy comparator requires the reference-comparison environment profile"
                ),
                case_id=self.benchmark_name,
            )
        self.lon = 12.34
        self.lat = 56.78
        try:
            from obspy.geodetics import FlinnEngdahl
        except ImportError as exc:
            record_state(
                self.benchmark_name,
                None,
                "build_unavailable",
                reason=f"required ObsPy import failed: {exc!r}",
            )
            raise
        self.obspy_lookup = FlinnEngdahl()
        value = int(self.obspy_lookup.get_number(self.lon, self.lat))
        _checked_setup(
            self.benchmark_name,
            None,
            lambda: _assert_equal(value, source_reference().number(self.lon, self.lat)),
        )

    def time_obspy_geographic_number(self) -> None:
        self.obspy_lookup.get_number(self.lon, self.lat)


class TimeSourceReferenceScalarNumber(_ScalarBase):
    pretty_name = "Pinned source-table scalar lookup → number"
    pretty_source = "Direct breakpoint-scanner baseline over hash-verified ObsPy 1.4.2 FE tables."
    benchmark_name = "source_reference_geographic_number"
    version = CASES[benchmark_name].semantic_version_hash

    def setup(self) -> None:
        _require_environment(self.benchmark_name, None)
        self.lon = 12.34
        self.lat = 56.78
        self.reference = source_reference()
        value = self.reference.number(self.lon, self.lat)
        _checked_setup(self.benchmark_name, None, lambda: _assert_valid_number(value))

    def time_source_reference_geographic_number(self) -> None:
        self.reference.number(self.lon, self.lat)


class TimeSourceReferenceBatch(_BatchBase):
    params: ClassVar[list[int]] = list(REFERENCE_LOAD_SIZES)
    pretty_name = "Pinned source-table batch-equivalent scan"
    pretty_source = (
        "Loop the direct pinned source-table scanner over the same deterministic coordinates."
    )
    benchmark_name = "source_reference_geographic_numbers"
    version = CASES[benchmark_name].semantic_version_hash

    def setup(self, size: int) -> None:
        super().setup(size)
        self.reference = source_reference()
        indices, expected = expected_geographic_numbers(
            self.coordinates,
            reference=self.reference,
        )
        _checked_setup(
            self.benchmark_name,
            size,
            lambda: _assert_source_sample(self.reference, self.coordinates, indices, expected),
        )

    def time_source_reference_geographic_numbers(self, size: int) -> None:
        np.fromiter(
            (
                self.reference.number(float(longitude), float(latitude))
                for longitude, latitude in self.coordinates
            ),
            dtype=np.uint16,
            count=size,
        )


def _assert_equal(observed: object, expected: object) -> None:
    if observed != expected:
        raise AssertionError(f"semantic mismatch: observed {observed!r}, expected {expected!r}")


def _assert_valid_number(value: int) -> None:
    if not 1 <= value <= 757:
        raise AssertionError(f"source scanner returned invalid geographic number: {value}")


def _assert_source_sample(
    reference: object,
    coordinate_values: np.ndarray,
    indices: np.ndarray,
    expected: np.ndarray,
) -> None:
    observed = np.fromiter(
        (
            reference.number(
                float(coordinate_values[index, 0]),
                float(coordinate_values[index, 1]),
            )
            for index in indices
        ),
        dtype=np.uint16,
        count=len(indices),
    )
    np.testing.assert_array_equal(observed, expected)
