from typing import TypeVar, Generic
from .primitive import Primitive

T = TypeVar("T")


class Align(Primitive, Generic[T]):
    """Represents align(x) — align a field to the current call point."""

    def __init__(self, value: T) -> None:
        self.value = value

    def __repr__(self) -> str:
        return f"Align({self.value!r})"
