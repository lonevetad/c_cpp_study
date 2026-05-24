from typing import TypeVar, Generic, Any
from .primitive import Primitive

T = TypeVar("T")


class Field(Primitive, Generic[T]):
    """Represents an FCPP field<T> — spatially-distributed value across all nodes."""

    def __init__(self, value: T) -> None:
        self.value = value

    def __repr__(self) -> str:
        return f"Field({self.value!r})"

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, Field):
            return False
        return self.value == other.value
