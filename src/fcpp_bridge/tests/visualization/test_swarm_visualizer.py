"""Tests for SwarmVisualizer — matplotlib-based live chart."""

import sys
import pytest
from unittest.mock import patch

from fcpp_bridge.ipc import NodeState, SwarmSnapshot
from fcpp_bridge.visualization import SwarmVisualizer


def _make_snapshot(round_number: int, values: list, sim_time: float = None) -> SwarmSnapshot:
    if sim_time is None:
        sim_time = round_number * 0.1
    nodes = [NodeState(node_id=i, state_data=v, timestamp=sim_time) for i, v in enumerate(values)]
    return SwarmSnapshot(round_number=round_number, time=sim_time, nodes=nodes)


def _bare_visualizer(**kwargs):
    """Create a SwarmVisualizer bypassing __init__ (no matplotlib needed)."""
    viz = SwarmVisualizer.__new__(SwarmVisualizer)
    viz._rounds = []
    viz._node_counts = []
    viz._means = []
    viz._mins = []
    viz._maxs = []
    viz._dirty = False
    viz._max_rounds = kwargs.get("max_rounds", 500)
    return viz


# ============================================================================
# Test 4: SwarmVisualizer — requires matplotlib
# ============================================================================


def test_swarm_visualizer_requires_matplotlib():
    with patch.dict(sys.modules, {"matplotlib.pyplot": None, "matplotlib.animation": None}):
        with pytest.raises((ImportError, Exception)):
            SwarmVisualizer()


# ============================================================================
# Test 5: SwarmVisualizer data accumulation (no display needed)
# ============================================================================


def test_swarm_visualizer_data_accumulation():
    viz = _bare_visualizer()
    viz.update(_make_snapshot(0, [10.0, 20.0, 30.0]))
    viz.update(_make_snapshot(1, [5.0, 15.0]))

    data = viz.get_data()
    assert data["rounds"] == [0, 1]
    assert data["node_counts"] == [3, 2]
    assert data["means"][0] == pytest.approx(20.0)
    assert data["means"][1] == pytest.approx(10.0)
    assert data["mins"][0] == pytest.approx(10.0)
    assert data["maxs"][0] == pytest.approx(30.0)


def test_swarm_visualizer_max_rounds_trim():
    viz = _bare_visualizer(max_rounds=5)
    for i in range(10):
        viz.update(_make_snapshot(i, [float(i)]))

    data = viz.get_data()
    assert len(data["rounds"]) == 5
    assert data["rounds"][0] == 5  # oldest retained round


def test_swarm_visualizer_empty_snapshot():
    viz = _bare_visualizer()
    snap = SwarmSnapshot(round_number=0, time=0.0, nodes=[])
    viz.update(snap)

    data = viz.get_data()
    assert data["node_counts"] == [0]
    assert data["means"] == [0.0]
    assert data["mins"] == [0.0]
    assert data["maxs"] == [0.0]


def test_swarm_visualizer_non_numeric_state_ignored():
    viz = _bare_visualizer()
    nodes = [
        NodeState(node_id=0, state_data="text", timestamp=0.0),
        NodeState(node_id=1, state_data=5.0, timestamp=0.0),
    ]
    snap = SwarmSnapshot(round_number=0, time=0.0, nodes=nodes)
    viz.update(snap)

    data = viz.get_data()
    assert data["means"] == [pytest.approx(5.0)]
    assert data["node_counts"] == [2]


# ============================================================================
# Test 6: dirty flag
# ============================================================================


def test_swarm_visualizer_dirty_flag_set_on_update():
    viz = _bare_visualizer()
    assert viz._dirty is False
    viz.update(_make_snapshot(0, [1.0]))
    assert viz._dirty is True


def test_swarm_visualizer_dirty_flag_cleared_by_animate():
    viz = _bare_visualizer()
    viz._ax_nodes = None
    viz._ax_values = None
    viz._dirty = True
    viz._redraw = lambda: None  # type: ignore[method-assign]
    viz._animate(0)
    assert viz._dirty is False
