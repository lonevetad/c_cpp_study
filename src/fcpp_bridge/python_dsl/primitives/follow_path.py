from typing import TypeVar, Generic
from .primitive import Primitive

T = TypeVar("T")


class FollowPath(Primitive, Generic[T]):
    """Represents follow_path(path, max_v, period) — follow a sequence of waypoints."""

    def __init__(self, path: T, max_v: float, period: float) -> None:
        self.path = path
        self.max_v = max_v
        self.period = period

    def __repr__(self) -> str:
        return f"FollowPath(max_v={self.max_v!r})"
