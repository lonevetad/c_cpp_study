from typing import TypeVar, Generic
from .primitive import Primitive

T = TypeVar("T")


class ExponentialFilter(Primitive, Generic[T]):
    """Represents exponential_filter(value, factor[, initial]) — exponential smoothing."""

    def __init__(self, value: T, factor: float, initial: T = None) -> None:
        self.value = value
        self.factor = factor
        self.initial = initial

    def __repr__(self) -> str:
        return f"ExponentialFilter({self.value!r}, factor={self.factor!r})"
