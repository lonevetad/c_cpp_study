from typing import TypeVar, Generic, Any
from .primitive import Primitive

T = TypeVar("T")


class ModOther(Primitive, Generic[T]):
    """Represents mod_other(x[, y]) — modify neighbour-side values of a field."""

    def __init__(self, value: T, modifier: Any = None) -> None:
        self.value = value
        self.modifier = modifier

    def __repr__(self) -> str:
        return f"ModOther({self.value!r})"
