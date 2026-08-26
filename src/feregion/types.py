"""Small public value types."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Region:
    """A Flinn-Engdahl region number and its packaged name."""

    number: int
    name: str
