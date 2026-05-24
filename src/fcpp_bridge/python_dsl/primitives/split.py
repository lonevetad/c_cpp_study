from typing import Any, Callable
from .primitive import Primitive


class Split(Primitive):
    """Represents split(key, func) — partition computation by key.
    ``func`` is a callable (C++ ``G&&``)."""

    has_callable_args = True
    callable_arg_positions = (1,)   # func at constructor index 1

    def __init__(self, key: Any, func: Callable) -> None:
        self.key = key
        self.func = func

    def __repr__(self) -> str:
        return f"Split(key={self.key!r}, func=<callable>)"
