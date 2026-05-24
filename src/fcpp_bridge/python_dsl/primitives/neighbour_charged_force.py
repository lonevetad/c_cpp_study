from .primitive import Primitive


class NeighbourChargedForce(Primitive):
    """Represents neighbour_charged_force(mass, charge) — electrostatic force from neighbours."""

    def __init__(self, mass: float, charge: float) -> None:
        self.mass = mass
        self.charge = charge

    def __repr__(self) -> str:
        return f"NeighbourChargedForce(mass={self.mass!r}, charge={self.charge!r})"
