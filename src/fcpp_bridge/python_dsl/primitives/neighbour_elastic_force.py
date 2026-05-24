from typing import Any
from .primitive import Primitive


class NeighbourElasticForce(Primitive):
    """Represents neighbour_elastic_force(length, strength) — elastic spring force from neighbours."""

    def __init__(self, length: Any, strength: Any) -> None:
        self.length = length
        self.strength = strength

    def __repr__(self) -> str:
        return f"NeighbourElasticForce(length={self.length!r})"
