from typing import TypeVar, Generic, Callable
from .primitive import Primitive

T = TypeVar("T")


class FoldHood(Primitive, Generic[T]):
    """Represents fold_hood(init, expr) — tree reduction over neighborhood.
    ``expr`` is a callable (C++ ``G&&``)."""

    has_callable_args = True
    callable_arg_positions = (1,)   # expr at constructor index 1

    def __init__(self, init: T, expr: Callable[[T, T], T]) -> None:
        self.init = init
        self.expr = expr

    def __repr__(self) -> str:
        return f"FoldHood(init={self.init!r}, expr=<callable>)"
