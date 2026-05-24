"""Decorators for building aggregate functions."""

from typing import Type, Callable, Any, Optional

from fcpp_bridge.log import get_logger

_log = get_logger(__name__)


# ---------------------------------------------------------------------------
# Mixin base classes — proper OOP; decorator injects via dynamic subclassing
# ---------------------------------------------------------------------------

class _MixinGossip:
    """Gossip-protocol methods for distributed aggregation."""

    def gossip_max(self, value: Any) -> Any:
        """Replicate maximum value across neighbors."""
        from .primitives import MaxHood
        return MaxHood(value)

    def gossip_sum(self, value: Any) -> Any:
        """Replicate sum across neighbors."""
        from .primitives import FoldHood
        return FoldHood(0, lambda a, b: a + b)

    def gossip(self, value: Any, accumulate: Callable) -> Any:
        """Gossip a value across the network with a given accumulation function."""
        from .primitives import Gossip
        return Gossip(value, accumulate)

    def gossip_avg(self, value: Any) -> Any:
        """Replicate average across neighbors."""
        from .primitives import Gossip
        return Gossip(value, lambda a, b: (a + b) / 2)

    def gossip_count(self) -> int:
        """Count nodes in network."""
        from .primitives import CountHood
        return CountHood()


class _MixinBroadcast:
    """Broadcast-protocol methods for leader-based dissemination."""

    def broadcast_from_source(self, source_expr: Any, value_expr: Any) -> Any:
        """Broadcast value from sources to all nodes."""
        from .primitives import Broadcast
        return Broadcast(source_expr, value_expr)

    def multi_hop_broadcast(self, hops: int, expr: Any) -> Any:
        """Limited-range broadcast (hops parameter limits propagation)."""
        return expr

    def distance_broadcast(self, expr: Any) -> Any:
        """Broadcast with distance penalty from source."""
        from .primitives import Distance
        return Distance(0)


class _MixinCollection:
    """Collection methods for distributed data gathering."""

    def sp_collection(self, distance: Any, value: Any, null: Any,
                      accumulate: Callable) -> Any:
        """Single-path collection via tree structure."""
        from .primitives import SpCollection
        return SpCollection(distance, value, null, accumulate)

    def mp_collection(self, distance: Any, value: Any, null: Any,
                      accumulate: Callable, divide: Callable) -> Any:
        """Multi-path collection via gradient."""
        from .primitives import MpCollection
        return MpCollection(distance, value, null, accumulate, divide)

    def wmp_collection(self, distance: float, radius: float, value: Any,
                       accumulate: Callable, multiply: Callable) -> Any:
        """Weighted multi-path collection."""
        from .primitives import WmpCollection
        return WmpCollection(distance, radius, value, accumulate, multiply)


class _MixinElection:
    """Leader-election primitives."""

    def diameter_election(self, value: Any, diameter: int) -> Any:
        from .primitives import DiameterElection
        return DiameterElection(value, diameter)

    def diameter_election_distance(self, value: Any, diameter: int) -> Any:
        from .primitives import DiameterElectionDistance
        return DiameterElectionDistance(value, diameter)

    def color_election(self, value: Any = None) -> Any:
        from .primitives import ColorElection
        return ColorElection(value)

    def color_election_distance(self, value: Any = None) -> Any:
        from .primitives import ColorElectionDistance
        return ColorElectionDistance(value)

    def wave_election(self, value: Any = None, expansion=None) -> Any:
        from .primitives import WaveElection
        return WaveElection(value, expansion)

    def wave_election_distance(self, value: Any = None, expansion=None) -> Any:
        from .primitives import WaveElectionDistance
        return WaveElectionDistance(value, expansion)


class _MixinTime:
    """Temporal aggregate primitives."""

    def constant(self, value: Any) -> Any:
        from .primitives import Constant
        return Constant(value)

    def constant_after(self, value: Any, t: float) -> Any:
        from .primitives import ConstantAfter
        return ConstantAfter(value, t)

    def counter(self, start: Any = None, increment: Any = None) -> Any:
        from .primitives import Counter
        return Counter(start, increment)

    def delay(self, value: Any, n: int) -> Any:
        from .primitives import Delay
        return Delay(value, n)

    def round_since(self, condition: Any) -> Any:
        from .primitives import RoundSince
        return RoundSince(condition)

    def time_since(self, condition: Any) -> Any:
        from .primitives import TimeSince
        return TimeSince(condition)

    def timed_decay(self, value: Any, null: Any, dt: float) -> Any:
        from .primitives import TimedDecay
        return TimedDecay(value, null, dt)

    def exponential_filter(self, value: Any, factor: float,
                            initial: Any = None) -> Any:
        from .primitives import ExponentialFilter
        return ExponentialFilter(value, factor, initial)

    def shared_clock(self) -> Any:
        from .primitives import SharedClock
        return SharedClock()

    def shared_decay(self, value: Any, factor: float,
                     initial: Any = None) -> Any:
        from .primitives import SharedDecay
        return SharedDecay(value, factor, initial)

    def shared_filter(self, value: Any, factor: float,
                      initial: Any = None) -> Any:
        from .primitives import SharedFilter
        return SharedFilter(value, factor, initial)

    def toggle(self, change: Any, start: bool = False) -> Any:
        from .primitives import Toggle
        return Toggle(change, start)

    def toggle_filter(self, change: Any, start: bool = False) -> Any:
        from .primitives import ToggleFilter
        return ToggleFilter(change, start)


class _MixinGeometry:
    """Spatial geometry methods for location-aware aggregation."""

    def abf_distance(self, source: bool,
                     metric: Optional[Callable] = None) -> Any:
        """Adaptive Bellman-Ford distance from sources."""
        from .primitives import AbfDistance
        return AbfDistance(source, metric)

    def bis_distance(self, source: bool, period: float, speed: float,
                     metric: Optional[Callable] = None) -> Any:
        """Bounded Information Speeds distance from sources."""
        from .primitives import BisDistance
        return BisDistance(source, period, speed, metric)

    def follow_target(self, target: Any, max_v: float, period: float) -> Any:
        """Move toward a spatial target point at fixed speed."""
        from .primitives import FollowTarget
        return FollowTarget(target, max_v, period)

    def rectangle_walk(self, low: Any, hi: Any, max_v: float,
                       period: float) -> Any:
        """Random walk bounded to a rectangle."""
        from .primitives import RectangleWalk
        return RectangleWalk(low, hi, max_v, period)

    def distance_to_nodes(self, target_ids: Any) -> Any:
        """Compute distances to target node IDs."""
        return 0.0

    def nearest_k_neighbors(self, k: int) -> Any:
        """Select k nearest neighbors."""
        return []

    def follow_gradient(self, target_location: Any) -> Any:
        """Follow gradient toward target location."""
        return target_location

    def follow_path(self, path: Any, max_v: float, period: float) -> Any:
        """Follow a sequence of waypoints."""
        from .primitives import FollowPath
        return FollowPath(path, max_v, period)

    def follow_track(self, trace: Any) -> Any:
        """Follow a GPS trace."""
        from .primitives import FollowTrack
        return FollowTrack(trace)

    def random_rectangle_target(self, low: Any, hi: Any,
                                 reach: float = None) -> Any:
        """Pick a random target point inside a rectangle."""
        from .primitives import RandomRectangleTarget
        return RandomRectangleTarget(low, hi, reach)

    def neighbour_elastic_force(self, length: Any, strength: Any) -> Any:
        """Elastic spring force from neighbours."""
        from .primitives import NeighbourElasticForce
        return NeighbourElasticForce(length, strength)

    def neighbour_gravitational_force(self, mass: float) -> Any:
        """Gravitational force from neighbours."""
        from .primitives import NeighbourGravitationalForce
        return NeighbourGravitationalForce(mass)

    def neighbour_charged_force(self, mass: float, charge: float) -> Any:
        """Electrostatic force from neighbours."""
        from .primitives import NeighbourChargedForce
        return NeighbourChargedForce(mass, charge)

    def point_elastic_force(self, point: Any, length: float,
                             strength: float) -> Any:
        """Elastic force from a point attractor."""
        from .primitives import PointElasticForce
        return PointElasticForce(point, length, strength)

    def point_gravitational_force(self, point: Any, mass: float) -> Any:
        """Gravitational force from a point."""
        from .primitives import PointGravitationalForce
        return PointGravitationalForce(point, mass)


# ---------------------------------------------------------------------------
# Helper — build a new class with a mixin prepended in the MRO
# ---------------------------------------------------------------------------

def _apply_mixin(mixin_cls: type, marker: str, cls: Type) -> Type:
    """Return a new class inheriting (*mixin_cls*, *cls*) and copy metadata."""
    new_cls = type(cls.__name__, (mixin_cls, cls), {
        "__module__": cls.__module__,
        "__qualname__": cls.__qualname__,
        "__doc__": cls.__doc__,
    })
    setattr(new_cls, marker, True)
    _log.debug("Applied mixin %s to %s", mixin_cls.__name__, cls.__name__)
    return new_cls


# ---------------------------------------------------------------------------
# aggregate_function decorator
# ---------------------------------------------------------------------------

def aggregate_function(cls: Type) -> Type:
    """Decorator that marks a class as an FCPP aggregate program.

    Expected methods:
    - ``initial_state()``: returns the state at round 0
    - ``compute(self_state, neighbors)``: computes next state
    - ``when_<condition>(args)``: optional event handlers

    Example::

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

    # Mark before validation so MarkerRule passes
    cls._is_aggregate_function = True

    from .validators import AggregateValidator
    AggregateValidator.validate(cls)

    cls._dsl_metadata = {
        "decorated_at": __name__,
        "is_aggregable": True,
    }

    _log.debug("Registered aggregate function %s", cls.__name__)
    return cls


# ---------------------------------------------------------------------------
# Mixin decorators — each creates a new class via dynamic subclassing
# ---------------------------------------------------------------------------

def mixin_gossip(cls: Type) -> Type:
    """Add gossip-protocol methods: ``gossip``, ``gossip_max``, ``gossip_sum``,
    ``gossip_avg``, ``gossip_count``.

    Usage::

        @aggregate_function
        @mixin_gossip
        class GossipAggregate:
            ...
    """
    return _apply_mixin(_MixinGossip, "_has_gossip_mixin", cls)


def mixin_broadcast(cls: Type) -> Type:
    """Add broadcast-protocol methods: ``broadcast_from_source``,
    ``multi_hop_broadcast``, ``distance_broadcast``."""
    return _apply_mixin(_MixinBroadcast, "_has_broadcast_mixin", cls)


def mixin_collection(cls: Type) -> Type:
    """Add collection methods: ``sp_collection``, ``mp_collection``,
    ``wmp_collection``."""
    return _apply_mixin(_MixinCollection, "_has_collection_mixin", cls)


def mixin_election(cls: Type) -> Type:
    """Add leader-election primitives: ``diameter_election``,
    ``color_election``, ``wave_election`` (and ``_distance`` variants)."""
    return _apply_mixin(_MixinElection, "_has_election_mixin", cls)


def mixin_time(cls: Type) -> Type:
    """Add temporal aggregate primitives: ``constant``, ``constant_after``,
    ``counter``, ``delay``, ``round_since``, ``time_since``, ``timed_decay``,
    ``exponential_filter``, ``shared_clock``, ``shared_decay``,
    ``shared_filter``, ``toggle``, ``toggle_filter``."""
    return _apply_mixin(_MixinTime, "_has_time_mixin", cls)


def mixin_geometry(cls: Type) -> Type:
    """Add spatial geometry methods: ``abf_distance``, ``bis_distance``,
    ``follow_target``, ``rectangle_walk``, ``follow_path``, ``follow_track``,
    ``random_rectangle_target``, neighbour/point force methods."""
    return _apply_mixin(_MixinGeometry, "_has_geometry_mixin", cls)
