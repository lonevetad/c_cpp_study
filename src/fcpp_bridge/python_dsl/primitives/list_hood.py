from typing import TypeVar, Generic, Any
from .primitive import Primitive

T = TypeVar("T")


class ListHood(Primitive, Generic[T]):
    """Represents list_hood(container, a[, self_val]) — collect neighbourhood into container."""

    def __init__(self, container: Any, expr: Any, self_value: Any = None) -> None:
        self.container = container
        self.expr = expr
        self.self_value = self_value

    def __repr__(self) -> str:
        return f"ListHood(expr={self.expr!r})"
