from typing import Any
from .primitive import Primitive


class LineElasticForce(Primitive):
    """Represents line_elastic_force(p, q, length, strength) — elastic force from a line attractor."""

    def __init__(self, p: Any, q: Any, length: float, strength: float) -> None:
        self.p = p
        self.q = q
        self.length = length
        self.strength = strength

    def __repr__(self) -> str:
        return f"LineElasticForce(length={self.length!r})"
