"""Tests for FCPP primitive classes — Tests 7, 9, 11-17."""

import pytest
from fcpp_bridge.python_dsl import (
    Neighborhood,
    OldValue,
    Field,
    Gossip, SpCollection, MpCollection, WmpCollection,
    BisDistance, AbfDistance, RectangleWalk, FollowTarget,
    NbrUid, OldNbr, Align, AlignInplace, ModOther, Split,
    SumHood, MeanHood, AllHood, AnyHood, ListHood,
    AbfHops, FlexDistance, BisKsourceBroadcast,
    GossipMin, GossipMax, GossipMean,
    ListIdemCollection, ListArithCollection,
    FollowPath, FollowTrack, RandomRectangleTarget,
    NeighbourElasticForce, NeighbourGravitationalForce, NeighbourChargedForce,
    LineElasticForce, PlaneElasticForce, PointElasticForce, PointGravitationalForce,
    DiameterElection, DiameterElectionDistance,
    ColorElection, ColorElectionDistance,
    WaveElection, WaveElectionDistance,
    Constant, ConstantAfter, Counter, Delay,
    RoundSince, TimeSince, TimedDecay, ExponentialFilter,
    SharedClock, SharedDecay, SharedFilter, Toggle, ToggleFilter,
)


# ============================================================================
# Test 7: Primitive types
# ============================================================================


def test_primitives_neighborhood():
    nbrs = Neighborhood([1.0, 2.0, 3.0])
    assert nbrs.values == [1.0, 2.0, 3.0]
    assert "Neighborhood" in repr(nbrs)


def test_primitives_old_value():
    old = OldValue(42.0)
    assert old.value == 42.0
    assert "OldValue" in repr(old)


def test_primitives_field():
    field = Field(3.14)
    assert field.value == 3.14
    assert "Field" in repr(field)


# ============================================================================
# Test 9: New primitives — Gossip, collection, distance, geometry
# ============================================================================


def test_gossip_creation():
    acc = lambda a, b: max(a, b)
    g = Gossip(1.0, acc)
    assert g.value == 1.0
    assert g.accumulate is acc
    assert "Gossip" in repr(g)


def test_sp_collection_creation():
    acc = lambda a, b: a + b
    s = SpCollection(2.0, 5.0, 0.0, acc)
    assert s.distance == 2.0
    assert s.value == 5.0
    assert s.null == 0.0
    assert "SpCollection" in repr(s)


def test_mp_collection_creation():
    acc = lambda a, b: a + b
    div = lambda a, n: a / n
    m = MpCollection(2.0, 5.0, 0.0, acc, div)
    assert m.distance == 2.0
    assert m.value == 5.0
    assert "MpCollection" in repr(m)


def test_wmp_collection_creation():
    acc = lambda a, b: a + b
    mul = lambda a, w: a * w
    w = WmpCollection(2.0, 10.0, 5.0, acc, mul)
    assert w.distance == 2.0
    assert w.radius == 10.0
    assert w.value == 5.0
    assert "WmpCollection" in repr(w)


def test_bis_distance_creation():
    b = BisDistance(True, 0.5, 3.0)
    assert b.source is True
    assert b.period == 0.5
    assert b.speed == 3.0
    assert b.metric is None
    assert "BisDistance" in repr(b)


def test_bis_distance_with_metric():
    metric = lambda a, b: abs(a - b)
    b = BisDistance(False, 1.0, 5.0, metric)
    assert b.metric is metric


def test_abf_distance_creation():
    a = AbfDistance(True)
    assert a.source is True
    assert a.metric is None
    assert "AbfDistance" in repr(a)


def test_abf_distance_with_metric():
    metric = lambda a, b: abs(a - b)
    a = AbfDistance(False, metric)
    assert a.metric is metric


def test_rectangle_walk_creation():
    r = RectangleWalk((0.0, 0.0), (10.0, 10.0), 1.5, 0.1)
    assert r.low == (0.0, 0.0)
    assert r.hi == (10.0, 10.0)
    assert r.max_v == 1.5
    assert r.period == 0.1
    assert "RectangleWalk" in repr(r)


def test_follow_target_creation():
    f = FollowTarget((5.0, 5.0), 2.0, 0.1)
    assert f.target == (5.0, 5.0)
    assert f.max_v == 2.0
    assert f.period == 0.1
    assert "FollowTarget" in repr(f)


# ============================================================================
# Test 11: basics.hpp new primitives
# ============================================================================


def test_nbr_uid():
    n = NbrUid()
    assert "NbrUid" in repr(n)
    assert n == NbrUid()


def test_oldnbr():
    op = lambda a, b: a + b
    o = OldNbr(0.0, op)
    assert o.initial == 0.0
    assert "OldNbr" in repr(o)


def test_align():
    a = Align(1.0)
    assert a.value == 1.0
    assert "Align" in repr(a)


def test_align_inplace():
    a = AlignInplace(2.0)
    assert a.value == 2.0
    assert "AlignInplace" in repr(a)


def test_mod_other():
    m = ModOther(3.0)
    assert m.value == 3.0
    assert "ModOther" in repr(m)


def test_split():
    s = Split("key", lambda: None)
    assert s.key == "key"
    assert "Split" in repr(s)


# ============================================================================
# Test 12: utils.hpp new hood reductions
# ============================================================================


def test_sum_hood():
    s = SumHood(1.0)
    assert s.expr == 1.0
    assert "SumHood" in repr(s)


def test_mean_hood():
    m = MeanHood(2.0)
    assert m.expr == 2.0
    assert "MeanHood" in repr(m)


def test_all_hood():
    a = AllHood(True)
    assert a.expr is True
    assert "AllHood" in repr(a)


def test_any_hood():
    a = AnyHood(False)
    assert a.expr is False
    assert "AnyHood" in repr(a)


def test_list_hood():
    l = ListHood([], 1.0)
    assert l.expr == 1.0
    assert "ListHood" in repr(l)


# ============================================================================
# Test 13: spreading.hpp additions
# ============================================================================


def test_abf_hops():
    a = AbfHops(True)
    assert a.source is True
    assert "AbfHops" in repr(a)


def test_flex_distance():
    f = FlexDistance(True, 0.1, 5.0, 1.2, 3)
    assert f.source is True
    assert f.epsilon == 0.1
    assert f.radius == 5.0
    assert "FlexDistance" in repr(f)


def test_bis_ksource_broadcast():
    b = BisKsourceBroadcast(True, 42.0, 3, 0.5, 2.0)
    assert b.source is True
    assert b.k == 3
    assert b.value == 42.0
    assert "BisKsourceBroadcast" in repr(b)


# ============================================================================
# Test 14: collection.hpp additions
# ============================================================================


def test_gossip_min():
    g = GossipMin(5.0)
    assert g.value == 5.0
    assert "GossipMin" in repr(g)


def test_gossip_max():
    g = GossipMax(5.0)
    assert g.value == 5.0
    assert "GossipMax" in repr(g)


def test_gossip_mean():
    g = GossipMean(5.0)
    assert g.value == 5.0
    assert "GossipMean" in repr(g)


def test_list_idem_collection():
    acc = lambda a, b: a + b
    l = ListIdemCollection(1.0, 2.0, 3.0, 4.0, 0.0, 0.01, acc)
    assert l.distance == 1.0
    assert l.value == 2.0
    assert "ListIdemCollection" in repr(l)


def test_list_arith_collection():
    acc = lambda a, b: a + b
    l = ListArithCollection(1.0, 2.0, 3.0, 4.0, 0.0, 0.01, acc)
    assert l.distance == 1.0
    assert "ListArithCollection" in repr(l)


# ============================================================================
# Test 15: geometry.hpp additions
# ============================================================================


def test_follow_path():
    fp = FollowPath([(0, 0), (1, 1)], 1.0, 0.1)
    assert fp.max_v == 1.0
    assert "FollowPath" in repr(fp)


def test_follow_track():
    ft = FollowTrack("gps_trace_obj")
    assert ft.trace == "gps_trace_obj"
    assert "FollowTrack" in repr(ft)


def test_random_rectangle_target():
    r = RandomRectangleTarget((0, 0), (10, 10))
    assert r.reach is None
    assert "RandomRectangleTarget" in repr(r)


def test_random_rectangle_target_with_reach():
    r = RandomRectangleTarget((0, 0), (10, 10), reach=5.0)
    assert r.reach == 5.0


def test_neighbour_elastic_force():
    f = NeighbourElasticForce(1.0, 2.0)
    assert f.length == 1.0
    assert "NeighbourElasticForce" in repr(f)


def test_neighbour_gravitational_force():
    f = NeighbourGravitationalForce(9.8)
    assert f.mass == 9.8
    assert "NeighbourGravitationalForce" in repr(f)


def test_neighbour_charged_force():
    f = NeighbourChargedForce(1.0, 2.0)
    assert f.mass == 1.0
    assert f.charge == 2.0
    assert "NeighbourChargedForce" in repr(f)


def test_line_elastic_force():
    f = LineElasticForce((0, 0), (1, 0), 1.0, 2.0)
    assert f.length == 1.0
    assert "LineElasticForce" in repr(f)


def test_plane_elastic_force():
    f = PlaneElasticForce((0, 0, 0), (0, 0, 1), 1.0, 2.0)
    assert f.length == 1.0
    assert "PlaneElasticForce" in repr(f)


def test_point_elastic_force():
    f = PointElasticForce((5, 5), 1.0, 2.0)
    assert f.length == 1.0
    assert "PointElasticForce" in repr(f)


def test_point_gravitational_force():
    f = PointGravitationalForce((5, 5), 9.8)
    assert f.mass == 9.8
    assert "PointGravitationalForce" in repr(f)


# ============================================================================
# Test 16: election.hpp
# ============================================================================


def test_diameter_election():
    e = DiameterElection(42, 10)
    assert e.value == 42
    assert e.diameter == 10
    assert "DiameterElection" in repr(e)


def test_diameter_election_distance():
    e = DiameterElectionDistance(42, 10)
    assert e.diameter == 10
    assert "DiameterElectionDistance" in repr(e)


def test_color_election_no_value():
    e = ColorElection()
    assert e.value is None
    assert "ColorElection" in repr(e)


def test_color_election_with_value():
    e = ColorElection(7)
    assert e.value == 7


def test_color_election_distance():
    e = ColorElectionDistance(7)
    assert e.value == 7
    assert "ColorElectionDistance" in repr(e)


def test_wave_election():
    e = WaveElection()
    assert e.value is None
    assert "WaveElection" in repr(e)


def test_wave_election_distance():
    e = WaveElectionDistance(5)
    assert e.value == 5
    assert "WaveElectionDistance" in repr(e)


# ============================================================================
# Test 17: time.hpp
# ============================================================================


def test_constant():
    c = Constant(3.14)
    assert c.value == 3.14
    assert "Constant" in repr(c)


def test_constant_after():
    c = ConstantAfter(1.0, 5.0)
    assert c.value == 1.0
    assert c.t == 5.0
    assert "ConstantAfter" in repr(c)


def test_counter_default():
    c = Counter()
    assert c.start is None
    assert "Counter" in repr(c)


def test_counter_with_start():
    c = Counter(start=10)
    assert c.start == 10


def test_delay():
    d = Delay(1.0, 3)
    assert d.value == 1.0
    assert d.n == 3
    assert "Delay" in repr(d)


def test_round_since():
    r = RoundSince(True)
    assert r.condition is True
    assert "RoundSince" in repr(r)


def test_time_since():
    t = TimeSince(False)
    assert t.condition is False
    assert "TimeSince" in repr(t)


def test_timed_decay():
    t = TimedDecay(1.0, 0.0, 10.0)
    assert t.value == 1.0
    assert t.null == 0.0
    assert t.dt == 10.0
    assert "TimedDecay" in repr(t)


def test_exponential_filter():
    e = ExponentialFilter(5.0, 0.9)
    assert e.value == 5.0
    assert e.factor == 0.9
    assert e.initial is None
    assert "ExponentialFilter" in repr(e)


def test_shared_clock():
    s = SharedClock()
    assert "SharedClock" in repr(s)
    assert s == SharedClock()


def test_shared_decay():
    s = SharedDecay(1.0, 0.5)
    assert s.value == 1.0
    assert s.factor == 0.5
    assert "SharedDecay" in repr(s)


def test_shared_filter():
    s = SharedFilter(2.0, 0.8)
    assert s.value == 2.0
    assert "SharedFilter" in repr(s)


def test_toggle():
    t = Toggle(True)
    assert t.change is True
    assert t.start is False
    assert "Toggle" in repr(t)


def test_toggle_filter():
    t = ToggleFilter(False, start=True)
    assert t.start is True
    assert "ToggleFilter" in repr(t)
