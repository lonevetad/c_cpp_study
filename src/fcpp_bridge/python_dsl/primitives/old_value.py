from typing import TypeVar, Generic, Any
from .primitive import Primitive

T = TypeVar("T")


class OldValue(Primitive, Generic[T]):
    """Represents old<T> — value from previous round."""

    def __init__(self, value: T) -> None:
        self.value = value

    def __repr__(self) -> str:
        return f"OldValue({self.value!r})"

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, OldValue):
            return False
        return self.value == other.value
