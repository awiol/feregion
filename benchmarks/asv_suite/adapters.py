"""Historical public-interface adapters used by the ASV benchmark suite."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import numpy as np


class CapabilityUnavailable(RuntimeError):
    """Indicate that a historical package revision cannot implement one case semantically."""


@dataclass(slots=True)
class PackageAdapter:
    """Map stable benchmark operations onto the installed feregion public interface."""

    module: Any

    @classmethod
    def installed(cls) -> PackageAdapter:
        """Create an adapter for the feregion revision installed by ASV."""

        import feregion

        return cls(feregion)

    def _function(self, preferred: str, legacy: str | None = None) -> Callable[..., Any]:
        function = getattr(self.module, preferred, None)
        if callable(function):
            return function
        if legacy is not None:
            function = getattr(self.module, legacy, None)
            if callable(function):
                return function
        raise CapabilityUnavailable(f"installed revision lacks capability {preferred!r}")

    def lookup_geographic_number(self, lon: float, lat: float) -> int:
        return int(self._function("lookup_geographic_number", "lookup_number")(lon, lat))

    def lookup_geographic_region(self, lon: float, lat: float) -> object:
        return self._function("lookup_geographic_region", "lookup_region")(lon, lat)

    def geographic_number_to_name(self, number: int) -> str:
        return str(self._function("geographic_number_to_name", "number_to_name")(number))

    def lookup_geographic_numbers(self, coordinates: np.ndarray[Any, Any]) -> np.ndarray[Any, Any]:
        return np.asarray(
            self._function("lookup_geographic_numbers", "lookup_numbers")(coordinates)
        )

    def lookup_seismic_number(self, lon: float, lat: float) -> int:
        return int(self._function("lookup_seismic_number")(lon, lat))

    def lookup_seismic_region(self, lon: float, lat: float) -> object:
        return self._function("lookup_seismic_region")(lon, lat)

    def lookup_seismic_numbers(self, coordinates: np.ndarray[Any, Any]) -> np.ndarray[Any, Any]:
        return np.asarray(self._function("lookup_seismic_numbers")(coordinates))

    def geographic_numbers_to_seismic_numbers(
        self, numbers: np.ndarray[Any, Any]
    ) -> np.ndarray[Any, Any]:
        return np.asarray(self._function("geographic_numbers_to_seismic_numbers")(numbers))

    def geographic_numbers_to_names(self, numbers: np.ndarray[Any, Any]) -> np.ndarray[Any, Any]:
        return np.asarray(
            self._function("geographic_numbers_to_names", "numbers_to_names")(numbers)
        )

    def pandas_lookup(self, frame: object, *, include_names: bool) -> object:
        try:
            from feregion.pandas import lookup_dataframe
        except (ImportError, ModuleNotFoundError) as exc:
            raise CapabilityUnavailable("installed revision lacks pandas lookup adapter") from exc
        return lookup_dataframe(frame, include_names=include_names)
