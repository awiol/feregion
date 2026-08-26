"""Fetch and verify the pinned ObsPy Flinn-Engdahl source tables."""

from __future__ import annotations

import argparse
import os
import tempfile
from collections.abc import Callable, Mapping
from pathlib import Path
from urllib.request import Request, urlopen

from tools.obspy_fe_source import (
    DEFAULT_SOURCE_DIR,
    OBSPY_COMMIT,
    OBSPY_REVISION,
    RAW_BASE_URL,
    SOURCE_SHA256,
    sha256_bytes,
    verify_source_dir,
)

FetchBytes = Callable[[str], bytes]


def download_bytes(url: str) -> bytes:
    """Download one upstream file with a bounded network timeout."""

    request = Request(url, headers={"User-Agent": "feregion-source-fetch/0.1"})
    with urlopen(request, timeout=30) as response:
        return response.read()


def fetch_source_data(
    output_dir: Path = DEFAULT_SOURCE_DIR,
    *,
    fetch_bytes: FetchBytes = download_bytes,
    expected_sha256: Mapping[str, str] = SOURCE_SHA256,
) -> None:
    """Fetch the pinned FE tables and publish each file after hash verification.

    Existing valid files are retained. A downloaded file is written to a
    temporary sibling and atomically moved into place only after its SHA-256
    digest matches the pinned value.
    """

    output_dir.mkdir(parents=True, exist_ok=True)
    for name, expected_digest in expected_sha256.items():
        destination = output_dir / name
        if destination.is_file() and sha256_bytes(destination.read_bytes()) == expected_digest:
            continue

        url = f"{RAW_BASE_URL}/{name}"
        data = fetch_bytes(url)
        observed_sha256 = sha256_bytes(data)
        if observed_sha256 != expected_digest:
            raise ValueError(
                f"downloaded {name} from ObsPy {OBSPY_REVISION} ({OBSPY_COMMIT}) "
                "has unexpected SHA-256: "
                f"expected {expected_digest}, got {observed_sha256}"
            )

        temporary_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="wb",
                dir=output_dir,
                prefix=f".{name}.",
                suffix=".tmp",
                delete=False,
            ) as stream:
                stream.write(data)
                temporary_path = Path(stream.name)
            os.replace(temporary_path, destination)
            temporary_path = None
        finally:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)

    verify_source_dir(output_dir, expected_sha256)


def main() -> None:
    """Run the pinned source-data fetch command."""

    parser = argparse.ArgumentParser(
        description=(
            f"Fetch ObsPy {OBSPY_REVISION} Flinn-Engdahl source tables from "
            f"commit {OBSPY_COMMIT}."
        )
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_SOURCE_DIR,
        help="local cache directory for hash-verified pinned source tables",
    )
    args = parser.parse_args()
    fetch_source_data(args.output_dir)
    print(
        f"verified ObsPy {OBSPY_REVISION} ({OBSPY_COMMIT}) FE source data "
        f"in {args.output_dir}"
    )


if __name__ == "__main__":
    main()
