from typing import Any
from .primitive import Primitive


class SelfUid(Primitive):
    """Represents self_uid() — this device's unique identifier.

    In Python: always returns 0 (node UID is not accessible in the DSL layer).
    In C++:    transpiles to ``node.uid`` (direct field access, no CALL counter).

    Unlike FCPP coordination primitives (nbr, spawn, …), self_uid() does NOT
    increment the CALL counter, so it is safe to call inside match/case branches
    or if/else arms without causing CALL-counter desynchronisation.
    """

    def __init__(self) -> None:
        pass

    def __repr__(self) -> str:
        return "SelfUid()"

    def __eq__(self, other: Any) -> bool:
        return isinstance(other, SelfUid)
