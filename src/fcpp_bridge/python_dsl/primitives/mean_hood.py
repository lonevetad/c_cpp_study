from typing import TypeVar, Generic, Any
from .primitive import Primitive

T = TypeVar("T")


class MeanHood(Primitive, Generic[T]):
    """Represents mean_hood(a[, self_val]) — neighbourhood mean."""

    def __init__(self, expr: Any, self_value: Any = None) -> None:
        self.expr = expr
        self.self_value = self_value

    def __repr__(self) -> str:
        return f"MeanHood({self.expr!r})"
