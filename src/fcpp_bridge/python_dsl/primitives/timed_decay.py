from typing import TypeVar, Generic
from .primitive import Primitive

T = TypeVar("T")


class TimedDecay(Primitive, Generic[T]):
    """Represents timed_decay(value, null, dt) — value that decays to null over time dt."""

    def __init__(self, value: T, null: T, dt: float) -> None:
        self.value = value
        self.null = null
        self.dt = dt

    def __repr__(self) -> str:
        return f"TimedDecay({self.value!r}, null={self.null!r}, dt={self.dt!r})"
