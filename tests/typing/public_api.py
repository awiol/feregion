"""Static downstream-consumer fixture for the distributed typed public API."""

from __future__ import annotations

import numpy as np
import numpy.typing as npt

import feregion

coordinates: npt.NDArray[np.float64] = np.asarray([[12.0, 48.0]], dtype=np.float64)
geographic_number: int = feregion.lookup_geographic_number(12.0, 48.0)
numpy_geographic_number: int = feregion.lookup_geographic_number(np.int16(12), np.float32(48))
geographic_numbers: npt.NDArray[np.uint16] = feregion.lookup_geographic_numbers(coordinates)
longitude: npt.NDArray[np.float64] = coordinates[:, 0]
latitude: npt.NDArray[np.float64] = coordinates[:, 1]
split_geographic_numbers: npt.NDArray[np.uint16] = feregion.lookup_geographic_numbers_from_vectors(
    longitude, latitude
)
geographic_name: str = feregion.geographic_number_to_name(geographic_number)
seismic_number: int = feregion.lookup_seismic_number(12.0, 48.0)
numpy_seismic_number: int = feregion.lookup_seismic_number(np.int32(12), np.float64(48))
seismic_numbers: npt.NDArray[np.uint8] = feregion.lookup_seismic_numbers(coordinates)
split_seismic_numbers: npt.NDArray[np.uint8] = feregion.lookup_seismic_numbers_from_vectors(
    longitude, latitude
)
seismic_name: str = feregion.seismic_number_to_name(seismic_number)

scalar_geographic_names: npt.NDArray[np.str_] = feregion.geographic_numbers_to_names(543)
scalar_seismic_numbers: npt.NDArray[np.uint8] = feregion.geographic_numbers_to_seismic_numbers(543)
scalar_seismic_names: npt.NDArray[np.str_] = feregion.seismic_numbers_to_names(36)
