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
    Gossip,
    SpCollection,
    MpCollection,
    WmpCollection,
    BisDistance,
    AbfDistance,
    RectangleWalk,
    FollowTarget,
    # basics.hpp
    NbrUid,
    OldNbr,
    Align,
    AlignInplace,
    ModOther,
    Split,
    # utils.hpp
    SumHood,
    MeanHood,
    AllHood,
    AnyHood,
    ListHood,
    # spreading.hpp
    AbfHops,
    FlexDistance,
    BisKsourceBroadcast,
    # collection.hpp
    GossipMin,
    GossipMax,
    GossipMean,
    ListIdemCollection,
    ListArithCollection,
    # geometry.hpp
    FollowPath,
    FollowTrack,
    RandomRectangleTarget,
    NeighbourElasticForce,
    NeighbourGravitationalForce,
    NeighbourChargedForce,
    LineElasticForce,
    PlaneElasticForce,
    PointElasticForce,
    PointGravitationalForce,
    # election.hpp
    DiameterElection,
    DiameterElectionDistance,
    ColorElection,
    ColorElectionDistance,
    WaveElection,
    WaveElectionDistance,
    # time.hpp
    Constant,
    ConstantAfter,
    Counter,
    Delay,
    RoundSince,
    TimeSince,
    TimedDecay,
    ExponentialFilter,
    SharedClock,
    SharedDecay,
    SharedFilter,
    Toggle,
    ToggleFilter,
)
from .decorators import (
    aggregate_function,
    mixin_gossip,
    mixin_broadcast,
    mixin_collection,
    mixin_geometry,
    mixin_election,
    mixin_time,
)
from .types import AggregateType, CppType
from .validators import AggregateValidator, ValidationError

__all__ = [
    # Original primitives
    "Field", "Neighborhood", "OldValue", "StateValue",
    "FoldHood", "MinHood", "MaxHood", "CountHood",
    "Spawn", "Broadcast", "Distance", "HopCount",
    "Gossip", "SpCollection", "MpCollection", "WmpCollection",
    "BisDistance", "AbfDistance", "RectangleWalk", "FollowTarget",
    # basics.hpp
    "NbrUid", "OldNbr", "Align", "AlignInplace", "ModOther", "Split",
    # utils.hpp
    "SumHood", "MeanHood", "AllHood", "AnyHood", "ListHood",
    # spreading.hpp
    "AbfHops", "FlexDistance", "BisKsourceBroadcast",
    # collection.hpp
    "GossipMin", "GossipMax", "GossipMean",
    "ListIdemCollection", "ListArithCollection",
    # geometry.hpp
    "FollowPath", "FollowTrack", "RandomRectangleTarget",
    "NeighbourElasticForce", "NeighbourGravitationalForce", "NeighbourChargedForce",
    "LineElasticForce", "PlaneElasticForce", "PointElasticForce", "PointGravitationalForce",
    # election.hpp
    "DiameterElection", "DiameterElectionDistance",
    "ColorElection", "ColorElectionDistance",
    "WaveElection", "WaveElectionDistance",
    # time.hpp
    "Constant", "ConstantAfter", "Counter", "Delay",
    "RoundSince", "TimeSince", "TimedDecay", "ExponentialFilter",
    "SharedClock", "SharedDecay", "SharedFilter", "Toggle", "ToggleFilter",
    # Decorators
    "aggregate_function",
    "mixin_gossip",
    "mixin_broadcast",
    "mixin_collection",
    "mixin_geometry",
    "mixin_election",
    "mixin_time",
    # Types & validation
    "AggregateType",
    "CppType",
    "AggregateValidator",
    "ValidationError",
]

__version__ = "0.1.0"
