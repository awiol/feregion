"""Bound HTTP response size for repository source-acquisition tools."""

from __future__ import annotations

import hashlib
from typing import Any

_READ_CHUNK_BYTES = 64 * 1024


class ResponseTooLargeError(ValueError):
    """Raised when a source response exceeds its explicit acquisition limit."""


def read_bounded_response_with_sha256(
    response: Any, *, max_bytes: int, label: str
) -> tuple[bytes, str]:
    """Read one bounded response and compute SHA-256 incrementally."""

    if max_bytes < 1:
        raise ValueError("max_bytes must be positive")
    headers = getattr(response, "headers", None)
    declared_value = headers.get("Content-Length") if headers is not None else None
    if declared_value is not None:
        try:
            declared_length = int(declared_value)
        except (TypeError, ValueError):
            declared_length = None
        if declared_length is not None and declared_length > max_bytes:
            raise ResponseTooLargeError(
                f"{label} declares {declared_length} bytes; limit is {max_bytes}"
            )
    payload = bytearray()
    digest = hashlib.sha256()
    while True:
        remaining = max_bytes - len(payload)
        chunk = response.read(min(_READ_CHUNK_BYTES, remaining + 1))
        if not chunk:
            break
        payload.extend(chunk)
        if len(payload) > max_bytes:
            raise ResponseTooLargeError(f"{label} exceeds {max_bytes} bytes")
        digest.update(chunk)
    return bytes(payload), digest.hexdigest()


def read_bounded_response(response: Any, *, max_bytes: int, label: str) -> bytes:
    """Read one response with a declared and actual byte ceiling."""

    payload, _ = read_bounded_response_with_sha256(response, max_bytes=max_bytes, label=label)
    return payload
