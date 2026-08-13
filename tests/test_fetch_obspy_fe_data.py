"""Tests for reproducible acquisition of the external ObsPy FE source tables."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from tools.fetch_obspy_fe_data import fetch_source_data
from tools.obspy_fe_source import RAW_BASE_URL, SOURCE_SHA256, sha256_file


def test_fetch_source_data_writes_verified_files(tmp_path: Path) -> None:
    """Verified downloads are published with their expected bytes and hashes."""

    payloads = {name: f"payload-for-{name}".encode() for name in SOURCE_SHA256}
    expected = {name: hashlib.sha256(data).hexdigest() for name, data in payloads.items()}

    fetch_source_data(
        tmp_path,
        fetch_bytes=lambda url: payloads[url.rsplit("/", 1)[-1]],
        expected_sha256=expected,
    )

    for name, data in payloads.items():
        assert (tmp_path / name).read_bytes() == data
        assert sha256_file(tmp_path / name) == expected[name]


def test_fetch_source_data_rejects_hash_mismatch(tmp_path: Path) -> None:
    """A file with unexpected upstream bytes is not published."""

    name = next(iter(SOURCE_SHA256))

    with pytest.raises(ValueError, match="unexpected SHA-256"):
        fetch_source_data(tmp_path, fetch_bytes=lambda _url: b"wrong")

    assert not (tmp_path / name).exists()


def test_fetch_source_data_uses_pinned_raw_urls(tmp_path: Path) -> None:
    """Every network request uses the pinned ObsPy raw-source base URL."""

    seen: list[str] = []

    def fetch(url: str) -> bytes:
        seen.append(url)
        return b"wrong"

    with pytest.raises(ValueError, match="unexpected SHA-256"):
        fetch_source_data(tmp_path, fetch_bytes=fetch)

    first_name = next(iter(SOURCE_SHA256))
    assert seen == [f"{RAW_BASE_URL}/{first_name}"]
