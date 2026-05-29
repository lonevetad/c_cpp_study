"""Tests for NodeState and SwarmSnapshot dataclasses."""

import pytest
from fcpp_bridge.ipc import NodeState, SwarmSnapshot


# ============================================================================
# Test 1: Data structures
# ============================================================================


def test_node_state_creation():
    state = NodeState(node_id=0, state_data=42.0, timestamp=1.5)
    assert state.node_id == 0
    assert state.state_data == 42.0
    assert state.timestamp == 1.5


def test_swarm_snapshot_creation():
    nodes = [
        NodeState(node_id=0, state_data=1.0, timestamp=0.0),
        NodeState(node_id=1, state_data=2.0, timestamp=0.0),
    ]
    snapshot = SwarmSnapshot(round_number=0, time=0.0, nodes=nodes)
    assert snapshot.round_number == 0
    assert len(snapshot.nodes) == 2
    assert snapshot.nodes[0].node_id == 0


def test_swarm_snapshot_empty():
    snapshot = SwarmSnapshot(round_number=0, time=0.0, nodes=[])
    assert len(snapshot.nodes) == 0


# ============================================================================
# Test 6: NodeState edge cases
# ============================================================================


def test_node_state_dict_state_data():
    state = NodeState(node_id=5, state_data={"x": 1.0, "y": 2.0}, timestamp=3.0)
    assert state.state_data["x"] == 1.0
    assert state.node_id == 5


def test_node_state_list_state_data():
    state = NodeState(node_id=0, state_data=[1, 2, 3], timestamp=0.0)
    assert len(state.state_data) == 3


def test_node_state_none_state_data():
    state = NodeState(node_id=0, state_data=None, timestamp=0.0)
    assert state.state_data is None


def test_swarm_snapshot_many_nodes():
    nodes = [NodeState(node_id=i, state_data=float(i), timestamp=1.0) for i in range(50)]
    snap = SwarmSnapshot(round_number=1, time=1.0, nodes=nodes)
    assert len(snap.nodes) == 50
    assert snap.nodes[49].node_id == 49


def test_swarm_snapshot_round_zero():
    snap = SwarmSnapshot(round_number=0, time=0.0, nodes=[])
    assert snap.round_number == 0
    assert snap.time == 0.0
