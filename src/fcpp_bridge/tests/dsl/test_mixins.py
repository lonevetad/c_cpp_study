"""Tests for mixin decorators — geometry, collection, gossip, election, time."""

import pytest
from fcpp_bridge.python_dsl import (
    aggregate_function, Neighborhood,
    Gossip, SpCollection, MpCollection, WmpCollection,
    BisDistance, AbfDistance, RectangleWalk, FollowTarget,
    DiameterElection, ColorElection, WaveElection,
    Constant, Toggle, SharedClock,
)
from fcpp_bridge.python_dsl.decorators import (
    mixin_geometry, mixin_collection, mixin_gossip,
    mixin_election, mixin_time,
)


# ============================================================================
# Test 10: mixin_geometry and mixin_collection return proper primitive objects
# ============================================================================


def test_mixin_geometry_abf_distance():
    @aggregate_function
    @mixin_geometry
    class GeoAgg:
        def initial_state(self) -> float:
            return 0.0
        def compute(self, self_state: float, neighbors: Neighborhood[float]) -> float:
            return self_state

    obj = GeoAgg()
    result = GeoAgg.abf_distance(obj, True)
    assert isinstance(result, AbfDistance)
    assert result.source is True


def test_mixin_geometry_bis_distance():
    @aggregate_function
    @mixin_geometry
    class GeoAgg2:
        def initial_state(self) -> float:
            return 0.0
        def compute(self, self_state: float, neighbors: Neighborhood[float]) -> float:
            return self_state

    obj = GeoAgg2()
    result = GeoAgg2.bis_distance(obj, False, 0.5, 3.0)
    assert isinstance(result, BisDistance)
    assert result.source is False


def test_mixin_geometry_rectangle_walk():
    @aggregate_function
    @mixin_geometry
    class GeoAgg3:
        def initial_state(self) -> float:
            return 0.0
        def compute(self, self_state: float, neighbors: Neighborhood[float]) -> float:
            return self_state

    obj = GeoAgg3()
    result = GeoAgg3.rectangle_walk(obj, (0, 0), (10, 10), 1.0, 0.1)
    assert isinstance(result, RectangleWalk)


def test_mixin_geometry_follow_target():
    @aggregate_function
    @mixin_geometry
    class GeoAgg4:
        def initial_state(self) -> float:
            return 0.0
        def compute(self, self_state: float, neighbors: Neighborhood[float]) -> float:
            return self_state

    obj = GeoAgg4()
    result = GeoAgg4.follow_target(obj, (5.0, 5.0), 2.0, 0.1)
    assert isinstance(result, FollowTarget)


def test_mixin_collection_sp_collection():
    @aggregate_function
    @mixin_collection
    class ColAgg:
        def initial_state(self) -> float:
            return 0.0
        def compute(self, self_state: float, neighbors: Neighborhood[float]) -> float:
            return self_state

    obj = ColAgg()
    result = ColAgg.sp_collection(obj, 1.0, 5.0, 0.0, lambda a, b: a + b)
    assert isinstance(result, SpCollection)


def test_mixin_collection_mp_collection():
    @aggregate_function
    @mixin_collection
    class ColAgg2:
        def initial_state(self) -> float:
            return 0.0
        def compute(self, self_state: float, neighbors: Neighborhood[float]) -> float:
            return self_state

    obj = ColAgg2()
    result = ColAgg2.mp_collection(obj, 1.0, 5.0, 0.0, lambda a, b: a + b, lambda a, n: a / n)
    assert isinstance(result, MpCollection)


def test_mixin_collection_wmp_collection():
    @aggregate_function
    @mixin_collection
    class ColAgg3:
        def initial_state(self) -> float:
            return 0.0
        def compute(self, self_state: float, neighbors: Neighborhood[float]) -> float:
            return self_state

    obj = ColAgg3()
    result = ColAgg3.wmp_collection(obj, 1.0, 5.0, 3.0, lambda a, b: a + b, lambda a, w: a * w)
    assert isinstance(result, WmpCollection)


def test_mixin_gossip_gossip_method():
    @aggregate_function
    @mixin_gossip
    class GossipAgg:
        def initial_state(self) -> float:
            return 0.0
        def compute(self, self_state: float, neighbors: Neighborhood[float]) -> float:
            return self_state

    obj = GossipAgg()
    result = GossipAgg.gossip(obj, 5.0, lambda a, b: max(a, b))
    assert isinstance(result, Gossip)
    assert result.value == 5.0


# ============================================================================
# Test 18: mixin_election and mixin_time
# ============================================================================


def test_mixin_election_diameter():
    @aggregate_function
    @mixin_election
    class ElAgg:
        def initial_state(self) -> float:
            return 0.0
        def compute(self, self_state: float, neighbors: Neighborhood[float]) -> float:
            return self_state
    obj = ElAgg()
    result = ElAgg.diameter_election(obj, 5, 10)
    assert isinstance(result, DiameterElection)


def test_mixin_election_color():
    @aggregate_function
    @mixin_election
    class ElAgg2:
        def initial_state(self) -> float:
            return 0.0
        def compute(self, self_state: float, neighbors: Neighborhood[float]) -> float:
            return self_state
    obj = ElAgg2()
    result = ElAgg2.color_election(obj, 7)
    assert isinstance(result, ColorElection)
    assert result.value == 7


def test_mixin_election_wave():
    @aggregate_function
    @mixin_election
    class ElAgg3:
        def initial_state(self) -> float:
            return 0.0
        def compute(self, self_state: float, neighbors: Neighborhood[float]) -> float:
            return self_state
    obj = ElAgg3()
    result = ElAgg3.wave_election(obj)
    assert isinstance(result, WaveElection)


def test_mixin_time_constant():
    @aggregate_function
    @mixin_time
    class TiAgg:
        def initial_state(self) -> float:
            return 0.0
        def compute(self, self_state: float, neighbors: Neighborhood[float]) -> float:
            return self_state
    obj = TiAgg()
    result = TiAgg.constant(obj, 3.14)
    assert isinstance(result, Constant)


def test_mixin_time_toggle():
    @aggregate_function
    @mixin_time
    class TiAgg2:
        def initial_state(self) -> float:
            return 0.0
        def compute(self, self_state: float, neighbors: Neighborhood[float]) -> float:
            return self_state
    obj = TiAgg2()
    result = TiAgg2.toggle(obj, True)
    assert isinstance(result, Toggle)


def test_mixin_time_shared_clock():
    @aggregate_function
    @mixin_time
    class TiAgg3:
        def initial_state(self) -> float:
            return 0.0
        def compute(self, self_state: float, neighbors: Neighborhood[float]) -> float:
            return self_state
    obj = TiAgg3()
    result = TiAgg3.shared_clock(obj)
    assert isinstance(result, SharedClock)
