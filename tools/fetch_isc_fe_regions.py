"""Fetch, normalize, and verify the ISC Flinn-Engdahl hierarchy page."""

from __future__ import annotations

import argparse
import json
import os
import re
import tempfile
from html.parser import HTMLParser
from pathlib import Path
from urllib.request import Request, urlopen

from tools.isc_fe_source import (
    DEFAULT_ISC_SOURCE,
    EXPECTED_SEMANTIC_SHA256,
    ISC_FE_URL,
    RETIRED_GEOGRAPHIC_REGIONS,
    semantic_sha256,
)

_REGION_RE = re.compile(r"^Seismic Region\s+(\d+)$", re.IGNORECASE)
_GEOGRAPHIC_RE = re.compile(r"^(\d+)\s+(.+)$")


class _TextExtractor(HTMLParser):
    """Collect human-visible text while ignoring script and style content."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._ignored_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style"}:
            self._ignored_depth += 1
        elif tag in {"br", "p", "div", "li", "tr", "h1", "h2", "h3", "pre"}:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style"}:
            self._ignored_depth = max(0, self._ignored_depth - 1)
        elif tag in {"p", "div", "li", "tr", "h1", "h2", "h3", "pre"}:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self._ignored_depth:
            self.parts.append(data)


def download_bytes(url: str = ISC_FE_URL) -> bytes:
    """Download the current ISC FE standards page with a bounded timeout."""

    request = Request(url, headers={"User-Agent": "feregion-source-fetch/0.2"})
    with urlopen(request, timeout=30) as response:
        return response.read()


def _visible_lines(html: bytes) -> list[str]:
    """Return normalized non-empty visible-text lines from the ISC page."""

    parser = _TextExtractor()
    parser.feed(html.decode("utf-8"))
    text = "".join(parser.parts)
    return [" ".join(line.split()) for line in text.splitlines() if line.strip()]


def parse_isc_html(html: bytes) -> dict[str, object]:
    """Extract the 50 seismic names and geographical memberships from ISC HTML.

    The parser intentionally ignores the geographical labels because the
    runtime hierarchy needs only seismic names and geographical membership.
    Retired geographical identifiers are present on the ISC page but are
    removed from the active membership lists in the normalized document.
    """

    lines = _visible_lines(html)
    regions: list[dict[str, object]] = []
    index = 0
    while index < len(lines):
        match = _REGION_RE.match(lines[index])
        if match is None:
            index += 1
            continue

        number = int(match.group(1))
        if index + 1 >= len(lines):
            raise ValueError(f"ISC seismic region {number} has no name")
        name = lines[index + 1]
        geographic_regions: list[int] = []
        index += 2
        while index < len(lines) and _REGION_RE.match(lines[index]) is None:
            geographic = _GEOGRAPHIC_RE.match(lines[index])
            if geographic is not None:
                geographic_number = int(geographic.group(1))
                if 1 <= geographic_number <= 757:
                    geographic_regions.append(geographic_number)
            index += 1

        geographic_regions = sorted(
            number for number in set(geographic_regions) if number not in RETIRED_GEOGRAPHIC_REGIONS
        )
        regions.append(
            {
                "number": number,
                "name": name,
                "geographic_regions": geographic_regions,
            }
        )

    document: dict[str, object] = {
        "schema_version": 1,
        "source_url": ISC_FE_URL,
        "scheme_revision": "1995",
        "seismic_regions": regions,
    }
    _validate_normalized_document(document)
    return document


def _validate_normalized_document(document: dict[str, object]) -> None:
    """Validate complete hierarchy coverage before publication."""

    regions = document.get("seismic_regions")
    if not isinstance(regions, list) or len(regions) != 50:
        raise ValueError("ISC FE source must contain exactly 50 seismic regions")
    observed_numbers = [region.get("number") for region in regions if isinstance(region, dict)]
    if observed_numbers != list(range(1, 51)):
        raise ValueError("ISC seismic region numbers must be exactly 1 through 50")

    geographic = [
        number
        for region in regions
        if isinstance(region, dict)
        for number in region.get("geographic_regions", [])
    ]
    if len(geographic) != 754 or len(set(geographic)) != 754:
        raise ValueError("ISC hierarchy must map exactly 754 active geographical regions")
    if set(range(1, 758)) - set(geographic) != RETIRED_GEOGRAPHIC_REGIONS:
        raise ValueError("ISC hierarchy has unexpected geographical-region coverage")


def fetch_isc_source(
    output_path: Path = DEFAULT_ISC_SOURCE,
    *,
    fetch_bytes=download_bytes,
) -> None:
    """Fetch ISC hierarchy data, verify its semantic content, and publish JSON.

    HTML layout is not pinned byte-for-byte. The parsed hierarchy is normalized
    and compared by semantic SHA-256 so harmless page-layout changes do not
    invalidate the source while membership or packaged seismic names do.
    """

    document = parse_isc_html(fetch_bytes(ISC_FE_URL))
    observed = semantic_sha256(document)
    if observed != EXPECTED_SEMANTIC_SHA256:
        raise ValueError(
            "ISC FE hierarchy has changed: "
            f"expected semantic SHA-256 {EXPECTED_SEMANTIC_SHA256}, got {observed}"
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(document, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=output_path.parent,
            prefix=f".{output_path.name}.",
            suffix=".tmp",
            delete=False,
        ) as stream:
            stream.write(payload)
            temporary_path = Path(stream.name)
        os.replace(temporary_path, output_path)
        temporary_path = None
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def main() -> None:
    """Run the ISC FE source retrieval command."""

    parser = argparse.ArgumentParser(
        description="Fetch and verify ISC Flinn-Engdahl hierarchy data."
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_ISC_SOURCE)
    args = parser.parse_args()
    fetch_isc_source(args.output)
    print(f"verified ISC FE hierarchy in {args.output}")


if __name__ == "__main__":
    main()
