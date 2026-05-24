from typing import TypeVar, Generic
from .primitive import Primitive

T = TypeVar("T")


class SharedDecay(Primitive, Generic[T]):
    """Represents shared_decay(value, factor[, initial]) — network-wide decaying value."""

    def __init__(self, value: T, factor: float, initial: T = None) -> None:
        self.value = value
        self.factor = factor
        self.initial = initial

    def __repr__(self) -> str:
        return f"SharedDecay({self.value!r}, factor={self.factor!r})"
