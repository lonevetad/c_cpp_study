from typing import TypeVar, Generic, Any, List
from .primitive import Primitive

T = TypeVar("T")


class Neighborhood(Primitive, Generic[T]):
    """Represents nbr<T> — neighbor values in current round."""

    def __init__(self, values: List[T]) -> None:
        self.values = values if values else []

    def __repr__(self) -> str:
        return f"Neighborhood({self.values!r})"

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, Neighborhood):
            return False
        return self.values == other.values

    def __bool__(self) -> bool:
        return len(self.values) > 0

    def __len__(self) -> int:
        return len(self.values)
