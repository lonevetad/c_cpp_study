from .primitive import Primitive


class Distance(Primitive):
    """Represents distance from source — used in distance-based broadcasts."""

    def __init__(self, source_id: int) -> None:
        self.source_id = source_id

    def __repr__(self) -> str:
        return f"Distance(source={self.source_id})"
