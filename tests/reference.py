"""Independent source-table oracle used by source integration tests.

This helper intentionally does not call the generated dense-table builder. It
implements the reference breakpoint scan directly from the hash-verified pinned source
files so generation defects can be detected by a separate code path.
"""

from pathlib import Path

QUADRANTS = ("ne", "nw", "se", "sw")
FILES = {"ne": "nesect.asc", "nw": "nwsect.asc", "se": "sesect.asc", "sw": "swsect.asc"}


class SourceReference:
    """Parse retained FE source tables and perform a direct breakpoint scan."""

    def __init__(self, source_dir: Path) -> None:
        counts = [int(value) for value in (source_dir / "quadsidx.asc").read_text().split()]
        self.counts = {
            quadrant: counts[index * 91 : (index + 1) * 91]
            for index, quadrant in enumerate(QUADRANTS)
        }
        self.rows: dict[str, list[list[tuple[int, int]]]] = {}
        for quadrant in QUADRANTS:
            values = [int(value) for value in (source_dir / FILES[quadrant]).read_text().split()]
            pairs = list(zip(values[0::2], values[1::2], strict=True))
            rows: list[list[tuple[int, int]]] = []
            offset = 0
            for count in self.counts[quadrant]:
                rows.append(pairs[offset : offset + count])
                offset += count
            assert offset == len(pairs)
            self.rows[quadrant] = rows

    @staticmethod
    def quadrant(longitude: float, latitude: float) -> str:
        if longitude >= 0 and latitude >= 0:
            return "ne"
        if longitude < 0 and latitude >= 0:
            return "nw"
        if longitude >= 0 and latitude < 0:
            return "se"
        return "sw"

    def number(self, longitude: float, latitude: float) -> int:
        if longitude == -180:
            longitude = 180
        quadrant = self.quadrant(longitude, latitude)
        abs_longitude = int(abs(longitude))
        abs_latitude = int(abs(latitude))
        result = None
        for breakpoint, number in self.rows[quadrant][abs_latitude]:
            if breakpoint > abs_longitude:
                break
            result = number
        assert result is not None
        return result
