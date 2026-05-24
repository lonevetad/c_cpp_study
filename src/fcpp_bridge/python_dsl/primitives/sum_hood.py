from typing import TypeVar, Generic, Any
from .primitive import Primitive

T = TypeVar("T")


class SumHood(Primitive, Generic[T]):
    """Represents sum_hood(a[, self_val]) — neighbourhood sum."""

    def __init__(self, expr: Any, self_value: Any = None) -> None:
        self.expr = expr
        self.self_value = self_value

    def __repr__(self) -> str:
        return f"SumHood({self.expr!r})"
