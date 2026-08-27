"""Static downstream-consumer fixture for the distributed typed public API."""

from __future__ import annotations

import numpy as np
import numpy.typing as npt

import feregion

coordinates: npt.NDArray[np.float64] = np.asarray([[12.0, 48.0]], dtype=np.float64)
geographic_number: int = feregion.lookup_geographic_number(12.0, 48.0)
geographic_numbers: npt.NDArray[np.uint16] = feregion.lookup_geographic_numbers(coordinates)
geographic_name: str = feregion.geographic_number_to_name(geographic_number)
seismic_number: int = feregion.lookup_seismic_number(12.0, 48.0)
seismic_numbers: npt.NDArray[np.uint8] = feregion.lookup_seismic_numbers(coordinates)
seismic_name: str = feregion.seismic_number_to_name(seismic_number)
