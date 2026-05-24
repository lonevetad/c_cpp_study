from typing import TypeVar, Generic, Callable
from .primitive import Primitive

T = TypeVar("T")


class OldNbr(Primitive, Generic[T]):
    """Represents oldnbr(f0, op) — combined old + nbr (rep + share).
    ``op`` is a callable (C++ ``G&&``)."""

    has_callable_args = True
    callable_arg_positions = (1,)   # op at constructor index 1

    def __init__(self, initial: T, op: Callable) -> None:
        self.initial = initial
        self.op = op

    def __repr__(self) -> str:
        return f"OldNbr(initial={self.initial!r}, op=<callable>)"
