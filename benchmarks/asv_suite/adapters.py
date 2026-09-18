"""Historical public-interface adapters used by the ASV benchmark suite."""

from __future__ import annotations

import inspect
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

    def seismic_numbers_to_names(self, numbers: np.ndarray[Any, Any]) -> np.ndarray[Any, Any]:
        return np.asarray(self._function("seismic_numbers_to_names")(numbers))

    def pandas_lookup(
        self,
        frame: object,
        *,
        include_names: bool,
        inplace: bool = False,
        level: str = "geographic",
    ) -> object:
        try:
            from feregion.pandas import lookup_dataframe
        except (ImportError, ModuleNotFoundError) as exc:
            raise CapabilityUnavailable("installed revision lacks pandas lookup adapter") from exc

        parameters = inspect.signature(lookup_dataframe).parameters
        if inplace and "inplace" not in parameters:
            raise CapabilityUnavailable("installed revision lacks pandas in-place lookup")
        if level != "geographic" and "level" not in parameters:
            raise CapabilityUnavailable("installed revision lacks pandas seismic-level lookup")
        kwargs: dict[str, object] = {"include_names": include_names}
        if "inplace" in parameters:
            kwargs["inplace"] = inplace
        if "level" in parameters:
            kwargs["level"] = level
        return lookup_dataframe(frame, **kwargs)

    def _engine(self) -> object:
        getter = getattr(self.module, "get_default_lookup", None)
        if not callable(getter):
            raise CapabilityUnavailable("installed revision lacks default lookup engine access")
        return getter()

    def split_geographic_numbers(
        self,
        longitude: np.ndarray[Any, Any],
        latitude: np.ndarray[Any, Any],
    ) -> np.ndarray[Any, Any]:
        engine = self._engine()
        function = getattr(engine, "_lookup_geographic_numbers_from_vectors", None)
        if not callable(function):
            raise CapabilityUnavailable("installed revision lacks split geographic lookup")
        return np.asarray(function(longitude, latitude))

    def split_seismic_numbers(
        self,
        longitude: np.ndarray[Any, Any],
        latitude: np.ndarray[Any, Any],
    ) -> np.ndarray[Any, Any]:
        engine = self._engine()
        function = getattr(engine, "_lookup_seismic_numbers_from_vectors", None)
        if not callable(function):
            raise CapabilityUnavailable("installed revision lacks split seismic lookup")
        return np.asarray(function(longitude, latitude))
