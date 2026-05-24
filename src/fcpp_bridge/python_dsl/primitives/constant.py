from typing import TypeVar, Generic
from .primitive import Primitive

T = TypeVar("T")


class Constant(Primitive, Generic[T]):
    """Represents constant(value) — freeze a value across rounds."""

    def __init__(self, value: T) -> None:
        self.value = value

    def __repr__(self) -> str:
        return f"Constant({self.value!r})"
