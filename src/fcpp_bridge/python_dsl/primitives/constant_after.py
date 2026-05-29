from typing import TypeVar, Generic
from .primitive import Primitive

T = TypeVar("T")


class ConstantAfter(Primitive, Generic[T]):
    """Represents constant_after(value, t) — freeze value after time t."""

    def __init__(self, value: T, t: float) -> None:
        self.value = value
        self.t = t

    def __repr__(self) -> str:
        return f"ConstantAfter({self.value!r}, t={self.t!r})"
