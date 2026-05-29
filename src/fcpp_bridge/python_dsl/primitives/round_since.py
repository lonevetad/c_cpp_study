from typing import Any
from .primitive import Primitive


class RoundSince(Primitive):
    """Represents round_since(condition) — rounds elapsed since condition was true."""

    def __init__(self, condition: Any) -> None:
        self.condition = condition

    def __repr__(self) -> str:
        return f"RoundSince({self.condition!r})"
