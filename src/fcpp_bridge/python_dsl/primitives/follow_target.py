from typing import Any
from .primitive import Primitive


class FollowTarget(Primitive):
    """Represents follow_target(target, max_v, period) — move toward a spatial target point."""

    def __init__(self, target: Any, max_v: float, period: float) -> None:
        self.target = target
        self.max_v = max_v
        self.period = period

    def __repr__(self) -> str:
        return f"FollowTarget(target={self.target!r}, max_v={self.max_v!r})"
