from typing import Any
from .primitive import Primitive


class PointElasticForce(Primitive):
    """Represents point_elastic_force(point, length, strength) — elastic force from a point attractor."""

    def __init__(self, point: Any, length: float, strength: float) -> None:
        self.point = point
        self.length = length
        self.strength = strength

    def __repr__(self) -> str:
        return f"PointElasticForce(point={self.point!r})"
