from .primitive import Primitive


class HopCount(Primitive):
    """Represents hop count from source in multi-hop propagation."""

    def __init__(self) -> None:
        pass

    def __repr__(self) -> str:
        return "HopCount()"
