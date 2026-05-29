from typing import Any
from .primitive import Primitive


class FollowTrack(Primitive):
    """Represents follow_track(trace) — follow a GPS trace."""

    def __init__(self, trace: Any) -> None:
        self.trace = trace

    def __repr__(self) -> str:
        return f"FollowTrack(trace={self.trace!r})"
