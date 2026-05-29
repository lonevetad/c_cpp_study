from typing import TypeVar, Generic
from .primitive import Primitive

T = TypeVar("T")


class SharedFilter(Primitive, Generic[T]):
    """Represents shared_filter(value, factor[, initial]) — network-wide filtered value."""

    def __init__(self, value: T, factor: float, initial: T = None) -> None:
        self.value = value
        self.factor = factor
        self.initial = initial

    def __repr__(self) -> str:
        return f"SharedFilter({self.value!r}, factor={self.factor!r})"
