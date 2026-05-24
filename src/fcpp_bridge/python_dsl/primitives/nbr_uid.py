from typing import Any
from .primitive import Primitive


class NbrUid(Primitive):
    """Represents nbr_uid() — field of neighbour device identifiers."""

    def __init__(self) -> None:
        pass

    def __repr__(self) -> str:
        return "NbrUid()"

    def __eq__(self, other: Any) -> bool:
        return isinstance(other, NbrUid)
