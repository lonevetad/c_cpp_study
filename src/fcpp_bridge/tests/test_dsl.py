"""Tests for Python DSL — Phase 1 Validation."""

import pytest
from dataclasses import dataclass
from fcpp_bridge.python_dsl import (
    aggregate_function,
    Neighborhood,
    OldValue,
    Field,
    AggregateType,
)
from fcpp_bridge.python_dsl.validators import (
    AggregateValidator,
    ValidationError,
)


# ============================================================================
# Test 1: Basic DSL decorator and validation
# ============================================================================


def test_dsl_basic_aggregate():
    """Test basic aggregate function definition."""

    @aggregate_function
    class SimpleAverage:
        def initial_state(self) -> float:
            return 0.0

        def compute(self, self_state: float, neighbors: Neighborhood[float]) -> float:
            if not neighbors.values:
                return self_state
            avg = sum(neighbors.values) / len(neighbors.values)
            return 0.7 * self_state + 0.3 * avg

    assert hasattr(SimpleAverage, "_is_aggregate_function")
    assert SimpleAverage._is_aggregate_function is True


def test_dsl_missing_decorator():
    """Test that validation catches undecorated class."""
    class NotDecorated:
        def initial_state(self) -> float:
            return 0.0

        def compute(self, self_state: float, neighbors: Neighborhood[float]) -> float:
            return self_state

    with pytest.raises(ValidationError):
        AggregateValidator.validate(NotDecorated)


def test_dsl_missing_initial_state():
    """Test that missing initial_state raises error."""
    with pytest.raises(ValueError, match="initial_state"):

        @aggregate_function
        class BadAggregate1:
            def compute(self, self_state, neighbors):
                return self_state


def test_dsl_missing_compute():
    """Test that missing compute raises error."""
    with pytest.raises(ValueError, match="compute"):

        @aggregate_function
        class BadAggregate2:
            def initial_state(self) -> float:
                return 0.0


# ============================================================================
# Test 2: Type annotations validation
# ============================================================================


def test_dsl_missing_initial_state_return_type():
    """Test that missing return type annotation raises error."""
    with pytest.raises(ValidationError, match="return type annotation"):

        @aggregate_function
        class BadType1:
            def initial_state(self):  # missing return type
                return 0.0

            def compute(self, self_state: float, neighbors: Neighborhood[float]) -> float:
                return self_state


def test_dsl_missing_compute_return_type():
    """Test that missing compute return type raises error."""
    with pytest.raises(ValidationError, match="return type annotation"):

        @aggregate_function
        class BadType2:
            def initial_state(self) -> float:
                return 0.0

            def compute(self, self_state: float, neighbors: Neighborhood[float]):  # missing return
                return self_state


# ============================================================================
# Test 3: Method signature validation
# ============================================================================


def test_dsl_compute_signature_wrong_param_count():
    """Test that compute with wrong parameter count raises error."""
    with pytest.raises(ValidationError, match="exactly 2 parameters"):

        @aggregate_function
        class BadSig1:
            def initial_state(self) -> float:
                return 0.0

            def compute(self, self_state: float, neighbors: Neighborhood[float], extra) -> float:
                return self_state


def test_dsl_compute_signature_too_few_params():
    """Test that compute with too few parameters raises error."""
    with pytest.raises(ValidationError, match="exactly 2 parameters"):

        @aggregate_function
        class BadSig2:
            def initial_state(self) -> float:
                return 0.0

            def compute(self, self_state: float) -> float:
                return self_state


def test_dsl_initial_state_with_params():
    """Test that initial_state with parameters raises error."""
    with pytest.raises(ValidationError, match="takes no parameters"):

        @aggregate_function
        class BadSig3:
            def initial_state(self, x: float) -> float:
                return x

            def compute(self, self_state: float, neighbors: Neighborhood[float]) -> float:
                return self_state


# ============================================================================
# Test 4: Custom state types
# ============================================================================


def test_dsl_custom_struct_state():
    """Test aggregate with custom dataclass state."""

    @dataclass
    class NodeState:
        value: float
        counter: int

    @aggregate_function
    class StructAggregate:
        def initial_state(self) -> NodeState:
            return NodeState(value=0.0, counter=0)

        def compute(
            self, self_state: NodeState, neighbors: Neighborhood[NodeState]
        ) -> NodeState:
            new_value = self_state.value + 1.0
            return NodeState(value=new_value, counter=self_state.counter + 1)

    validator = AggregateValidator()
    warnings = validator.validate(StructAggregate)
    assert len(warnings) == 0
    state_type = AggregateValidator.get_state_type(StructAggregate)
    assert state_type is NodeState


def test_dsl_tuple_state():
    """Test aggregate with tuple state."""

    @aggregate_function
    class TupleAggregate:
        def initial_state(self) -> tuple[float, int]:
            return (0.0, 0)

        def compute(
            self, self_state: tuple[float, int], neighbors: Neighborhood[tuple[float, int]]
        ) -> tuple[float, int]:
            value, count = self_state
            return (value + 1.0, count + 1)

    warnings = AggregateValidator.validate(TupleAggregate)
    assert len(warnings) == 0


def test_dsl_list_state():
    """Test aggregate with list state."""

    @aggregate_function
    class ListAggregate:
        def initial_state(self) -> list[float]:
            return [0.0, 0.0, 0.0]

        def compute(
            self, self_state: list[float], neighbors: Neighborhood[list[float]]
        ) -> list[float]:
            return [x + 1.0 for x in self_state]

    warnings = AggregateValidator.validate(ListAggregate)
    assert len(warnings) == 0


# ============================================================================
# Test 5: State type extraction
# ============================================================================


def test_dsl_extract_state_type_float():
    """Test extracting float state type."""

    @aggregate_function
    class FloatAggregate:
        def initial_state(self) -> float:
            return 0.0

        def compute(self, self_state: float, neighbors: Neighborhood[float]) -> float:
            return self_state

    state_type = AggregateValidator.get_state_type(FloatAggregate)
    assert state_type is float


def test_dsl_extract_state_type_int():
    """Test extracting int state type."""

    @aggregate_function
    class IntAggregate:
        def initial_state(self) -> int:
            return 0

        def compute(self, self_state: int, neighbors: Neighborhood[int]) -> int:
            return self_state

    state_type = AggregateValidator.get_state_type(IntAggregate)
    assert state_type is int


def test_dsl_extract_state_type_custom():
    """Test extracting custom struct state type."""

    @dataclass
    class CustomState:
        x: float
        y: int

    @aggregate_function
    class CustomAggregate:
        def initial_state(self) -> CustomState:
            return CustomState(0.0, 0)

        def compute(
            self, self_state: CustomState, neighbors: Neighborhood[CustomState]
        ) -> CustomState:
            return self_state

    state_type = AggregateValidator.get_state_type(CustomAggregate)
    assert state_type is CustomState


# ============================================================================
# Test 6: Common mistakes detection
# ============================================================================


def test_dsl_warning_step_method():
    """Test warning when using 'step' instead of 'compute'."""

    @aggregate_function
    class HasStepMethod:
        def initial_state(self) -> float:
            return 0.0

        def compute(self, self_state: float, neighbors: Neighborhood[float]) -> float:
            return self_state

        def step(self):  # Common mistake
            pass

    warnings = AggregateValidator.validate(HasStepMethod)
    assert any("step" in w for w in warnings)


def test_dsl_warning_update_method():
    """Test warning when using 'update' instead of 'compute'."""

    @aggregate_function
    class HasUpdateMethod:
        def initial_state(self) -> float:
            return 0.0

        def compute(self, self_state: float, neighbors: Neighborhood[float]) -> float:
            return self_state

        def update(self):  # Common mistake
            pass

    warnings = AggregateValidator.validate(HasUpdateMethod)
    assert any("update" in w for w in warnings)


# ============================================================================
# Test 7: Primitive types
# ============================================================================


def test_primitives_neighborhood():
    """Test Neighborhood primitive."""
    nbrs = Neighborhood([1.0, 2.0, 3.0])
    assert nbrs.values == [1.0, 2.0, 3.0]
    assert "Neighborhood" in repr(nbrs)


def test_primitives_old_value():
    """Test OldValue primitive."""
    old = OldValue(42.0)
    assert old.value == 42.0
    assert "OldValue" in repr(old)


def test_primitives_field():
    """Test Field primitive."""
    field = Field(3.14)
    assert field.value == 3.14
    assert "Field" in repr(field)


# ============================================================================
# Test 8: Type inference
# ============================================================================


def test_type_inference_float():
    """Test C++ type inference for float."""
    cpp_type = AggregateType.infer(float)
    assert cpp_type.name == "double"
    assert cpp_type.is_primitive


def test_type_inference_int():
    """Test C++ type inference for int."""
    cpp_type = AggregateType.infer(int)
    assert cpp_type.name == "int"
    assert cpp_type.is_primitive


def test_type_inference_list():
    """Test C++ type inference for list."""
    cpp_type = AggregateType.infer(list[float])
    assert "vector" in cpp_type.name
    assert "double" in cpp_type.name


def test_type_inference_custom_struct():
    """Test C++ type inference for custom struct."""

    @dataclass
    class MyState:
        x: float
        y: int

    cpp_type = AggregateType.infer(MyState)
    assert cpp_type.name == "MyState"
    assert cpp_type.is_struct
    assert "x" in cpp_type.fields
    assert "y" in cpp_type.fields


# ============================================================================
# Test 9: New primitives — Gossip, collection, distance, geometry
# ============================================================================

from fcpp_bridge.python_dsl import (
    Gossip, SpCollection, MpCollection, WmpCollection,
    BisDistance, AbfDistance, RectangleWalk, FollowTarget,
)


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
# Test 10: mixin_geometry and mixin_collection return proper primitive objects
# ============================================================================

from fcpp_bridge.python_dsl.decorators import mixin_geometry, mixin_collection, mixin_gossip


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
# Test 11: basics.hpp new primitives
# ============================================================================

from fcpp_bridge.python_dsl import (
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


# ============================================================================
# Test 18: mixin_election and mixin_time
# ============================================================================

from fcpp_bridge.python_dsl.decorators import mixin_election, mixin_time


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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
