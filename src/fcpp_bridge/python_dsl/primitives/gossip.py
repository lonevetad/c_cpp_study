from typing import TypeVar, Generic, Callable
from .primitive import Primitive

T = TypeVar("T")


class Gossip(Primitive, Generic[T]):
    """Represents gossip(value, accumulate) — distributed gossip aggregation.
    ``accumulate`` is a callable (C++ ``G&&``)."""

    has_callable_args = True
    callable_arg_positions = (1,)   # accumulate at constructor index 1

    def __init__(self, value: T, accumulate: Callable[[T, T], T]) -> None:
        self.value = value
        self.accumulate = accumulate

    def __repr__(self) -> str:
        return f"Gossip(value={self.value!r}, accumulate=<callable>)"
