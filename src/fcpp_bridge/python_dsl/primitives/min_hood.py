from typing import TypeVar, Generic, Any
from .primitive import Primitive

T = TypeVar("T")


class MinHood(Primitive, Generic[T]):
    """Represents min_hood(expr) — minimum across neighborhood."""

    def __init__(self, expr: Any) -> None:
        self.expr = expr

    def __repr__(self) -> str:
        return f"MinHood({self.expr!r})"
