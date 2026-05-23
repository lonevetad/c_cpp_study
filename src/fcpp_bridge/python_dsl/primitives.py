"""Core FCPP DSL primitives — Field, Neighborhood, OldValue, etc."""

from typing import TypeVar, Generic, Any, List, Callable

T = TypeVar("T")


class Field(Generic[T]):
    """Represents an FCPP field<T> — spatially-distributed value across all nodes."""

    def __init__(self, value: T):
        self.value = value

    def __repr__(self) -> str:
        return f"Field({self.value!r})"

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, Field):
            return False
        return self.value == other.value


class Neighborhood(Generic[T]):
    """Represents nbr<T> — neighbor values in current round."""

    def __init__(self, values: List[T]):
        self.values = values if values else []

    def __repr__(self) -> str:
        return f"Neighborhood({self.values!r})"

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, Neighborhood):
            return False
        return self.values == other.values

    def __bool__(self) -> bool:
        """Empty neighborhood evaluates to False."""
        return len(self.values) > 0

    def __len__(self) -> int:
        return len(self.values)


class OldValue(Generic[T]):
    """Represents old<T> — value from previous round."""

    def __init__(self, value: T):
        self.value = value

    def __repr__(self) -> str:
        return f"OldValue({self.value!r})"

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, OldValue):
            return False
        return self.value == other.value


class StateValue:
    """Marker for current node's own state value."""

    def __repr__(self) -> str:
        return "StateValue()"

    def __eq__(self, other: Any) -> bool:
        return isinstance(other, StateValue)


class FoldHood(Generic[T]):
    """Represents fold_hood(init, expr) — tree reduction over neighborhood."""

    def __init__(self, init: T, expr: Callable[[T, T], T]):
        self.init = init
        self.expr = expr

    def __repr__(self) -> str:
        return f"FoldHood(init={self.init!r}, expr=<lambda>)"


class MinHood(Generic[T]):
    """Represents min_hood(expr) — minimum across neighborhood."""

    def __init__(self, expr: Any):
        self.expr = expr

    def __repr__(self) -> str:
        return f"MinHood({self.expr!r})"


class MaxHood(Generic[T]):
    """Represents max_hood(expr) — maximum across neighborhood."""

    def __init__(self, expr: Any):
        self.expr = expr

    def __repr__(self) -> str:
        return f"MaxHood({self.expr!r})"


class CountHood:
    """Represents count_hood() — count of neighbors."""

    def __repr__(self) -> str:
        return "CountHood()"

    def __eq__(self, other: Any) -> bool:
        return isinstance(other, CountHood)


class Spawn(Generic[T]):
    """Represents spawn(f) — parallel sub-computation."""

    def __init__(self, func: Callable[..., T]):
        self.func = func

    def __repr__(self) -> str:
        return f"Spawn({self.func.__name__})"


class Broadcast(Generic[T]):
    """Represents broadcast(source, expr) — multi-source dissemination."""

    def __init__(self, source_expr: Any, value_expr: Any):
        self.source = source_expr
        self.value = value_expr

    def __repr__(self) -> str:
        return f"Broadcast(source={self.source!r}, value={self.value!r})"


class Distance:
    """Represents distance from source — used in distance-based broadcasts."""

    def __init__(self, source_id: int):
        self.source_id = source_id

    def __repr__(self) -> str:
        return f"Distance(source={self.source_id})"


class HopCount:
    """Represents hop count from source in multi-hop propagation."""

    def __init__(self):
        pass

    def __repr__(self) -> str:
        return "HopCount()"
