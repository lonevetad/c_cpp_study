"""Tests for Primitive base class — Prototype pattern, callable-arg metadata (v0.9)."""

import pytest
from fcpp_bridge.python_dsl import Primitive
from fcpp_bridge.python_dsl.primitives import (
    Gossip, FoldHood, Spawn, SpCollection, MpCollection, WmpCollection,
    OldNbr, Split, FlexDistance, BisKsourceBroadcast, ListIdemCollection,
    ListArithCollection, WaveElection, WaveElectionDistance,
    BisDistance, AbfDistance,
    RectangleWalk, FollowTarget, GossipMin,
)


def test_primitive_base_is_parent():
    assert issubclass(RectangleWalk, Primitive)
    assert issubclass(Gossip, Primitive)
    assert issubclass(FoldHood, Primitive)
    assert issubclass(GossipMin, Primitive)


def test_primitive_has_callable_args_defaults_false():
    p = RectangleWalk((0, 0), (10, 10), 1.0, 0.5)
    assert p.has_callable_args is False
    assert p.callable_arg_positions == ()


def test_primitive_callable_arg_positions_fold_hood():
    assert FoldHood.has_callable_args is True
    assert FoldHood.callable_arg_positions == (1,)


def test_primitive_callable_arg_positions_spawn():
    assert Spawn.has_callable_args is True
    assert Spawn.callable_arg_positions == (0,)


def test_primitive_callable_arg_positions_gossip():
    assert Gossip.has_callable_args is True
    assert Gossip.callable_arg_positions == (1,)


def test_primitive_callable_arg_positions_sp_collection():
    assert SpCollection.has_callable_args is True
    assert SpCollection.callable_arg_positions == (3,)


def test_primitive_callable_arg_positions_mp_collection():
    assert MpCollection.has_callable_args is True
    assert MpCollection.callable_arg_positions == (3, 4)


def test_primitive_callable_arg_positions_wmp_collection():
    assert WmpCollection.has_callable_args is True
    assert WmpCollection.callable_arg_positions == (3, 4)


def test_primitive_callable_arg_positions_oldnbr():
    assert OldNbr.has_callable_args is True
    assert OldNbr.callable_arg_positions == (1,)


def test_primitive_callable_arg_positions_split():
    assert Split.has_callable_args is True
    assert Split.callable_arg_positions == (1,)


def test_primitive_callable_arg_positions_flex_distance():
    assert FlexDistance.has_callable_args is True
    assert FlexDistance.callable_arg_positions == (5,)


def test_primitive_callable_arg_positions_bis_ksource():
    assert BisKsourceBroadcast.has_callable_args is True
    assert BisKsourceBroadcast.callable_arg_positions == (5,)


def test_primitive_callable_arg_positions_list_idem():
    assert ListIdemCollection.has_callable_args is True
    assert ListIdemCollection.callable_arg_positions == (6,)


def test_primitive_callable_arg_positions_wave_election():
    assert WaveElection.has_callable_args is True
    assert WaveElection.callable_arg_positions == (1,)


def test_primitive_callable_arg_positions_wave_election_distance():
    assert WaveElectionDistance.has_callable_args is True
    assert WaveElectionDistance.callable_arg_positions == (1,)


def test_primitive_clone_returns_equal_copy():
    p = RectangleWalk((0, 0), (10, 10), 2.0, 1.0)
    q = p.clone()
    assert q is not p
    assert q.low == p.low
    assert q.max_v == p.max_v


def test_primitive_clone_with_overrides():
    p = RectangleWalk((0, 0), (10, 10), 2.0, 1.0)
    q = p.clone_with(max_v=5.0)
    assert q.max_v == 5.0
    assert q.low == p.low  # unchanged


def test_primitive_clone_with_bad_key_raises():
    p = RectangleWalk((0, 0), (10, 10), 2.0, 1.0)
    with pytest.raises(AttributeError):
        p.clone_with(nonexistent=99)


def test_primitive_repr_no_callable():
    p = RectangleWalk((0, 0), (10, 10), 2.0, 1.0)
    r = repr(p)
    assert "RectangleWalk" in r


def test_primitive_repr_with_callable():
    g = Gossip(1.0, lambda a, b: a + b)
    r = repr(g)
    assert "Gossip" in r
    assert "<callable>" in r


def test_primitive_eq_non_callable():
    a = RectangleWalk((0, 0), (10, 10), 2.0, 1.0)
    b = RectangleWalk((0, 0), (10, 10), 2.0, 1.0)
    assert a == b


def test_primitive_eq_callable_by_identity():
    acc = lambda a, b: a + b
    a = Gossip(1.0, acc)
    b = Gossip(1.0, acc)
    c = Gossip(1.0, lambda a, b: a + b)
    assert a == b       # same function object
    assert a != c       # different function objects
