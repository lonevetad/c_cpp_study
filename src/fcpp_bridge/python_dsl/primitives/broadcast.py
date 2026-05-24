from typing import TypeVar, Generic, Any
from .primitive import Primitive

T = TypeVar("T")


class Broadcast(Primitive, Generic[T]):
    """Represents broadcast(source, expr) — multi-source dissemination."""

    def __init__(self, source_expr: Any, value_expr: Any) -> None:
        self.source = source_expr
        self.value = value_expr

    def __repr__(self) -> str:
        return f"Broadcast(source={self.source!r}, value={self.value!r})"
