from typing import TypeVar, Generic, Callable
from .primitive import Primitive

T = TypeVar("T")


class Spawn(Primitive, Generic[T]):
    """Represents spawn(f) — parallel sub-computation.
    ``func`` is a callable (C++ ``G&&``)."""

    has_callable_args = True
    callable_arg_positions = (0,)   # func at constructor index 0

    def __init__(self, func: Callable[..., T]) -> None:
        self.func = func

    def __repr__(self) -> str:
        return f"Spawn({self.func.__name__})"
