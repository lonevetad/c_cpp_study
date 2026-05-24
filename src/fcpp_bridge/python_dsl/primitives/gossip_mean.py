from typing import TypeVar, Generic
from .primitive import Primitive

T = TypeVar("T")


class GossipMean(Primitive, Generic[T]):
    """Represents gossip_mean(value) — gossip the mean."""

    def __init__(self, value: T) -> None:
        self.value = value

    def __repr__(self) -> str:
        return f"GossipMean({self.value!r})"
