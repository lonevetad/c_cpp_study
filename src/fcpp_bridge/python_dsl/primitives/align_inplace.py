from typing import TypeVar, Generic
from .primitive import Primitive

T = TypeVar("T")


class AlignInplace(Primitive, Generic[T]):
    """Represents align_inplace(x) — align a field in-place."""

    def __init__(self, value: T) -> None:
        self.value = value

    def __repr__(self) -> str:
        return f"AlignInplace({self.value!r})"
