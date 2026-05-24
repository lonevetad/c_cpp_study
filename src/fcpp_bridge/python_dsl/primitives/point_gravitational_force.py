from typing import Any
from .primitive import Primitive


class PointGravitationalForce(Primitive):
    """Represents point_gravitational_force(point, mass) — gravitational force from a point."""

    def __init__(self, point: Any, mass: float) -> None:
        self.point = point
        self.mass = mass

    def __repr__(self) -> str:
        return f"PointGravitationalForce(point={self.point!r}, mass={self.mass!r})"
