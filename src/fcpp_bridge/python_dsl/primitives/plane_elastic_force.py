from typing import Any
from .primitive import Primitive


class PlaneElasticForce(Primitive):
    """Represents plane_elastic_force(p, q, length, strength) — elastic force from a plane."""

    def __init__(self, p: Any, q: Any, length: float, strength: float) -> None:
        self.p = p
        self.q = q
        self.length = length
        self.strength = strength

    def __repr__(self) -> str:
        return f"PlaneElasticForce(length={self.length!r})"
