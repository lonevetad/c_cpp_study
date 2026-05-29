from typing import TypeVar, Generic, Callable
from .primitive import Primitive

T = TypeVar("T")


class WaveElection(Primitive, Generic[T]):
    """Represents wave_election([value[, expansion]]) — wave-based leader election.
    ``expansion`` is an optional callable (C++ ``G&&``)."""

    has_callable_args = True
    callable_arg_positions = (1,)   # expansion at constructor index 1

    def __init__(self, value: T = None, expansion: Callable = None) -> None:
        self.value = value
        self.expansion = expansion

    def __repr__(self) -> str:
        return f"WaveElection(value={self.value!r})"
