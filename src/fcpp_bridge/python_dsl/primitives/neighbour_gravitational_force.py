from .primitive import Primitive


class NeighbourGravitationalForce(Primitive):
    """Represents neighbour_gravitational_force(mass) — gravitational force from neighbours."""

    def __init__(self, mass: float) -> None:
        self.mass = mass

    def __repr__(self) -> str:
        return f"NeighbourGravitationalForce(mass={self.mass!r})"
