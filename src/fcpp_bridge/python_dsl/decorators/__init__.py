"""FCPP DSL decorators package — mixin classes and aggregate function decorator."""

from typing import Type

from ._mixin_gossip import _MixinGossip
from ._mixin_broadcast import _MixinBroadcast
from ._mixin_collection import _MixinCollection
from ._mixin_election import _MixinElection
from ._mixin_time import _MixinTime
from ._mixin_geometry import _MixinGeometry
from fcpp_bridge.log import get_logger

_log = get_logger(__name__)


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

    cls._is_aggregate_function = True

    from fcpp_bridge.python_dsl.validators import AggregateValidator
    AggregateValidator.validate(cls)

    cls._dsl_metadata = {
        "decorated_at": __name__,
        "is_aggregable": True,
    }

    _log.debug("Registered aggregate function %s", cls.__name__)
    return cls


def mixin_gossip(cls: Type) -> Type:
    """Add gossip-protocol methods: ``gossip``, ``gossip_max``, ``gossip_sum``,
    ``gossip_avg``, ``gossip_count``."""
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


__all__ = [
    "_MixinGossip",
    "_MixinBroadcast",
    "_MixinCollection",
    "_MixinElection",
    "_MixinTime",
    "_MixinGeometry",
    "_apply_mixin",
    "aggregate_function",
    "mixin_gossip",
    "mixin_broadcast",
    "mixin_collection",
    "mixin_election",
    "mixin_time",
    "mixin_geometry",
]
