from typing import TypeVar, Generic, Any
from .primitive import Primitive

T = TypeVar("T")


class MaxHood(Primitive, Generic[T]):
    """Represents max_hood(expr) — maximum across neighborhood."""

    def __init__(self, expr: Any) -> None:
        self.expr = expr

    def __repr__(self) -> str:
        return f"MaxHood({self.expr!r})"
