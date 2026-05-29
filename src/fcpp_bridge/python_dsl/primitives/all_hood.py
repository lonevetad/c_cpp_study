from typing import TypeVar, Generic, Any
from .primitive import Primitive

T = TypeVar("T")


class AllHood(Primitive, Generic[T]):
    """Represents all_hood(a[, self_val]) — neighbourhood logical AND."""

    def __init__(self, expr: Any, self_value: Any = None) -> None:
        self.expr = expr
        self.self_value = self_value

    def __repr__(self) -> str:
        return f"AllHood({self.expr!r})"
