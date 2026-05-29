"""Tests for VisualizerBase — abstract interface and attach/detach."""

import io
import pytest

from fcpp_bridge.ipc import NodeState, SwarmSnapshot
from fcpp_bridge.metrics import MetricsCollector
from fcpp_bridge.visualization import VisualizerBase, TextDashboard


def _make_snapshot(round_number: int, values: list, sim_time: float = None) -> SwarmSnapshot:
    if sim_time is None:
        sim_time = round_number * 0.1
    nodes = [NodeState(node_id=i, state_data=v, timestamp=sim_time) for i, v in enumerate(values)]
    return SwarmSnapshot(round_number=round_number, time=sim_time, nodes=nodes)


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
    collector.record(_make_snapshot(0, [1.0]))
    assert dash._round_count == 1


def test_detach_unsubscribes():
    collector = MetricsCollector()
    dash = TextDashboard(stream=io.StringIO())
    dash.attach(collector)
    dash.detach(collector)
    collector.record(_make_snapshot(0, [1.0]))
    assert dash._round_count == 0
