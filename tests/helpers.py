"""Shared test assertions with explicit behavioral intent."""

from collections.abc import Iterator
from contextlib import contextmanager
from typing import TypeVar

import pytest

E = TypeVar("E", bound=BaseException)


@contextmanager
def raises_exact(
    exception_type: type[E], *, match: str | None = None
) -> Iterator[pytest.ExceptionInfo[E]]:
    """Assert that a call raises exactly ``exception_type``.

    ``pytest.raises`` normally accepts subclasses. Package exception tests use
    this helper because the public contract distinguishes several related error
    classes and a broader or narrower class can change caller behavior.
    """

    with pytest.raises(exception_type, match=match) as exception_info:
        yield exception_info
    assert type(exception_info.value) is exception_type
