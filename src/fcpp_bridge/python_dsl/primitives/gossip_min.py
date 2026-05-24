from typing import TypeVar, Generic
from .primitive import Primitive

T = TypeVar("T")


class GossipMin(Primitive, Generic[T]):
    """Represents gossip_min(value) — gossip the minimum."""

    def __init__(self, value: T) -> None:
        self.value = value

    def __repr__(self) -> str:
        return f"GossipMin({self.value!r})"
