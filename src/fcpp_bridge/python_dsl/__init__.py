"""FCPP Python DSL — Phase 1: DSL layer for aggregate functions."""

from .primitives import (
    Field,
    Neighborhood,
    OldValue,
    StateValue,
    FoldHood,
    MinHood,
    MaxHood,
    CountHood,
    Spawn,
    Broadcast,
    Distance,
    HopCount,
)
from .decorators import (
    aggregate_function,
    mixin_gossip,
    mixin_broadcast,
    mixin_collection,
    mixin_geometry,
)
from .types import AggregateType, CppType
from .validators import AggregateValidator, ValidationError

__all__ = [
    # Primitives
    "Field",
    "Neighborhood",
    "OldValue",
    "StateValue",
    "FoldHood",
    "MinHood",
    "MaxHood",
    "CountHood",
    "Spawn",
    "Broadcast",
    "Distance",
    "HopCount",
    # Decorators
    "aggregate_function",
    "mixin_gossip",
    "mixin_broadcast",
    "mixin_collection",
    "mixin_geometry",
    # Types & validation
    "AggregateType",
    "CppType",
    "AggregateValidator",
    "ValidationError",
]

__version__ = "0.1.0"
