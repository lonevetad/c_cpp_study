"""Tests for Phase 7 — Visualization plugin."""

import io
import sys
import pytest
from unittest.mock import patch

from fcpp_bridge.ipc import NodeState, SwarmSnapshot
from fcpp_bridge.metrics import MetricsCollector
from fcpp_bridge.visualization import (
    VisualizerBase,
    TextDashboard,
    SwarmVisualizer,
    create_visualizer,
)


# ============================================================================
# Helpers
# ============================================================================


def make_snapshot(round_number: int, values: list, sim_time: float = None) -> SwarmSnapshot:
    if sim_time is None:
        sim_time = round_number * 0.1
    nodes = [
        NodeState(node_id=i, state_data=v, timestamp=sim_time)
        for i, v in enumerate(values)
    ]
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
# Test 1: VisualizerBase is abstract
# ============================================================================


def test_visualizer_base_is_abstract():
    with pytest.raises(TypeError):
        VisualizerBase()  # type: ignore[abstract]


# ============================================================================
# Test 2: attach / detach
# ============================================================================


def test_attach_subscribes_to_collector():
    collector = MetricsCollector()
    dash = TextDashboard(stream=io.StringIO())
    dash.attach(collector)
    collector.record(make_snapshot(0, [1.0]))
    assert dash._round_count == 1


def test_detach_unsubscribes():
    collector = MetricsCollector()
    dash = TextDashboard(stream=io.StringIO())
    dash.attach(collector)
    dash.detach(collector)
    collector.record(make_snapshot(0, [1.0]))
    assert dash._round_count == 0


# ============================================================================
# Test 3: TextDashboard
# ============================================================================


def test_text_dashboard_start_stop():
    buf = io.StringIO()
    dash = TextDashboard(stream=buf)
    dash.start()
    dash.stop()
    output = buf.getvalue()
    assert "FCPP Swarm Monitor" in output
    assert "Stopped" in output


def test_text_dashboard_update_numeric():
    buf = io.StringIO()
    dash = TextDashboard(stream=buf)
    dash.update(make_snapshot(42, [10.0, 20.0, 30.0]))
    output = buf.getvalue()
    assert "42" in output
    assert "20.0000" in output  # mean of [10, 20, 30]


def test_text_dashboard_update_no_numeric():
    buf = io.StringIO()
    dash = TextDashboard(stream=buf)
    nodes = [NodeState(node_id=0, state_data="hello", timestamp=0.0)]
    snap = SwarmSnapshot(round_number=1, time=0.1, nodes=nodes)
    dash.update(snap)
    output = buf.getvalue()
    assert "1" in output
    assert "no numeric state" in output


def test_text_dashboard_round_count():
    dash = TextDashboard(stream=io.StringIO())
    for i in range(5):
        dash.update(make_snapshot(i, [float(i)]))
    assert dash._round_count == 5


def test_text_dashboard_replay_from_history():
    collector = MetricsCollector()
    for i in range(3):
        collector.record(make_snapshot(i, [float(i)]))

    buf = io.StringIO()
    dash = TextDashboard(stream=buf)
    dash.replay_from_history(collector)
    lines = [ln for ln in buf.getvalue().splitlines() if ln.strip()]
    assert len(lines) == 3


# ============================================================================
# Test 4: SwarmVisualizer — requires matplotlib
# ============================================================================


def test_swarm_visualizer_requires_matplotlib():
    """SwarmVisualizer raises ImportError when matplotlib is unavailable."""
    # Patch the modules dict so that 'import matplotlib.pyplot' raises ImportError
    with patch.dict(sys.modules, {"matplotlib.pyplot": None, "matplotlib.animation": None}):
        with pytest.raises((ImportError, Exception)):
            SwarmVisualizer()


# ============================================================================
# Test 5: SwarmVisualizer data accumulation (no display needed)
# ============================================================================


def test_swarm_visualizer_data_accumulation():
    viz = _bare_visualizer()
    viz.update(make_snapshot(0, [10.0, 20.0, 30.0]))
    viz.update(make_snapshot(1, [5.0, 15.0]))

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
        viz.update(make_snapshot(i, [float(i)]))

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
    assert data["means"] == [pytest.approx(5.0)]   # only numeric node counted
    assert data["node_counts"] == [2]               # both nodes counted regardless


# ============================================================================
# Test 6: dirty flag
# ============================================================================


def test_swarm_visualizer_dirty_flag_set_on_update():
    viz = _bare_visualizer()
    assert viz._dirty is False
    viz.update(make_snapshot(0, [1.0]))
    assert viz._dirty is True


def test_swarm_visualizer_dirty_flag_cleared_by_animate():
    viz = _bare_visualizer()
    viz._ax_nodes = None
    viz._ax_values = None

    # Manually set dirty; _animate should call _redraw which requires axes,
    # so patch _redraw to a no-op.
    viz._dirty = True
    viz._redraw = lambda: None  # type: ignore[method-assign]
    viz._animate(0)
    assert viz._dirty is False


# ============================================================================
# Test 7: create_visualizer factory
# ============================================================================


def test_create_visualizer_text_when_prefer_gui_false():
    viz = create_visualizer(prefer_gui=False)
    assert isinstance(viz, TextDashboard)


def test_create_visualizer_text_fallback_when_no_matplotlib():
    with patch.dict(sys.modules, {"matplotlib.pyplot": None, "matplotlib.animation": None}):
        viz = create_visualizer(prefer_gui=True)
        assert isinstance(viz, TextDashboard)


def test_create_visualizer_attaches_to_collector():
    collector = MetricsCollector()
    buf = io.StringIO()
    viz = create_visualizer(collector=collector, prefer_gui=False, stream=buf)
    collector.record(make_snapshot(0, [1.0]))
    assert viz._round_count == 1


def test_create_visualizer_no_collector_no_attach():
    viz = create_visualizer(prefer_gui=False)
    assert isinstance(viz, TextDashboard)
    assert viz._round_count == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
