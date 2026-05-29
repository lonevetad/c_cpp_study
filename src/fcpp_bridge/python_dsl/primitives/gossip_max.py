from typing import TypeVar, Generic
from .primitive import Primitive

T = TypeVar("T")


class GossipMax(Primitive, Generic[T]):
    """Represents gossip_max(value) — gossip the maximum."""

    def __init__(self, value: T) -> None:
        self.value = value

    def __repr__(self) -> str:
        return f"GossipMax({self.value!r})"
