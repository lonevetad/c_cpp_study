"""Decorators for building aggregate functions."""

from typing import Type, Callable, Any
from functools import wraps


def aggregate_function(cls: Type) -> Type:
    """
    Decorator for aggregate function classes.

    Marks a class as an FCPP aggregate program. Expected methods:
    - initial_state(): returns the state at round 0
    - compute(self_state, neighbors): computes next state
    - when_<condition>(args): optional event handlers

    Example:
        @aggregate_function
        class MyAggregate:
            def initial_state(self) -> float:
                return 0.0

            def compute(self, self_state: float, neighbors) -> float:
                return self_state + 1.0
    """
    if not hasattr(cls, "initial_state"):
        raise ValueError(f"{cls.__name__} must define initial_state() method")

    if not hasattr(cls, "compute"):
        raise ValueError(f"{cls.__name__} must define compute(self_state, neighbors) method")

    # Mark the class as an aggregate function
    cls._is_aggregate_function = True

    # Store DSL metadata
    cls._dsl_metadata = {
        "decorated_at": __name__,
        "is_aggregable": True,
    }

    return cls


def mixin_gossip(cls: Type) -> Type:
    """
    Mixin: adds gossip-protocol methods for distributed aggregation.

    Provides methods for:
    - gossip_max(expr): replicate maximum across network
    - gossip_sum(expr): replicate sum across network
    - gossip_avg(expr): replicate average across network
    - gossip_count(): count nodes in network

    Usage:
        @aggregate_function
        @mixin_gossip
        class GossipAggregate:
            ...

    Example inside compute():
        max_value = self.gossip_max(self_state)
    """
    cls._has_gossip_mixin = True

    def gossip_max(self, value: Any) -> Any:
        """Replicate maximum value across neighbors."""
        from .primitives import MaxHood

        return MaxHood(value)

    def gossip_sum(self, value: Any) -> Any:
        """Replicate sum across neighbors."""
        from .primitives import FoldHood

        return FoldHood(0, lambda a, b: a + b)

    def gossip_avg(self, value: Any) -> Any:
        """Replicate average across neighbors."""
        # Will be expanded in Phase 2
        return value

    def gossip_count(self) -> int:
        """Count nodes in network."""
        from .primitives import CountHood

        return CountHood()

    cls.gossip_max = gossip_max
    cls.gossip_sum = gossip_sum
    cls.gossip_avg = gossip_avg
    cls.gossip_count = gossip_count

    return cls


def mixin_broadcast(cls: Type) -> Type:
    """
    Mixin: adds broadcast-protocol methods for leader-based dissemination.

    Provides methods for:
    - broadcast_from_source(source_expr, value_expr): single/multi-source broadcast
    - multi_hop_broadcast(hops, expr): limited-range broadcast
    - distance_broadcast(expr): disseminate by distance from source

    Usage:
        @aggregate_function
        @mixin_broadcast
        class BroadcastAggregate:
            ...
    """
    cls._has_broadcast_mixin = True

    def broadcast_from_source(self, source_expr: Any, value_expr: Any) -> Any:
        """Broadcast value from sources to all nodes."""
        from .primitives import Broadcast

        return Broadcast(source_expr, value_expr)

    def multi_hop_broadcast(self, hops: int, expr: Any) -> Any:
        """Limited-range broadcast (hops parameter limits propagation)."""
        # Will be expanded in Phase 2
        return expr

    def distance_broadcast(self, expr: Any) -> Any:
        """Broadcast with distance penalty from source."""
        from .primitives import Distance

        return Distance(0)

    cls.broadcast_from_source = broadcast_from_source
    cls.multi_hop_broadcast = multi_hop_broadcast
    cls.distance_broadcast = distance_broadcast

    return cls


def mixin_collection(cls: Type) -> Type:
    """
    Mixin: adds collection methods for distributed data gathering.

    Provides methods for:
    - sp_collection(expr): single-path collection (tree-based)
    - mp_collection(expr): multi-path collection (gradient-based)
    - wmp_collection(expr): weighted multi-path collection

    Usage:
        @aggregate_function
        @mixin_collection
        class CollectionAggregate:
            ...
    """
    cls._has_collection_mixin = True

    def sp_collection(self, expr: Any) -> Any:
        """Single-path collection via tree structure."""
        # Will be expanded in Phase 2
        return expr

    def mp_collection(self, expr: Any) -> Any:
        """Multi-path collection via gradient."""
        # Will be expanded in Phase 2
        return expr

    def wmp_collection(self, expr: Any, weights: Any = None) -> Any:
        """Weighted multi-path collection."""
        # Will be expanded in Phase 2
        return expr

    cls.sp_collection = sp_collection
    cls.mp_collection = mp_collection
    cls.wmp_collection = wmp_collection

    return cls


def mixin_geometry(cls: Type) -> Type:
    """
    Mixin: adds spatial geometry methods for location-aware aggregation.

    Provides methods for:
    - distance_to_nodes(target_ids): compute distances
    - nearest_k_neighbors(k): select k nearest nodes
    - follow_gradient(target_location): gradient-following

    Usage:
        @aggregate_function
        @mixin_geometry
        class GeometricAggregate:
            ...
    """
    cls._has_geometry_mixin = True

    def distance_to_nodes(self, target_ids: Any) -> Any:
        """Compute distances to target node IDs."""
        # Will be expanded in Phase 2
        return 0.0

    def nearest_k_neighbors(self, k: int) -> Any:
        """Select k nearest neighbors."""
        # Will be expanded in Phase 2
        return []

    def follow_gradient(self, target_location: Any) -> Any:
        """Follow gradient toward target location."""
        # Will be expanded in Phase 2
        return target_location

    cls.distance_to_nodes = distance_to_nodes
    cls.nearest_k_neighbors = nearest_k_neighbors
    cls.follow_gradient = follow_gradient

    return cls
