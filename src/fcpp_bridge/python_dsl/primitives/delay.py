from typing import TypeVar, Generic
from .primitive import Primitive

T = TypeVar("T")


class Delay(Primitive, Generic[T]):
    """Represents delay(value, n) — delay a value by n rounds."""

    def __init__(self, value: T, n: int) -> None:
        self.value = value
        self.n = n

    def __repr__(self) -> str:
        return f"Delay({self.value!r}, n={self.n!r})"
