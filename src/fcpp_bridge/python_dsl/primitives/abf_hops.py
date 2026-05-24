from .primitive import Primitive


class AbfHops(Primitive):
    """Represents abf_hops(source) — hop-count distance via Adaptive Bellman-Ford."""

    def __init__(self, source: bool) -> None:
        self.source = source

    def __repr__(self) -> str:
        return f"AbfHops(source={self.source!r})"
