"""Tests for create_visualizer factory function."""

import io
import sys
import pytest
from unittest.mock import patch

from fcpp_bridge.ipc import NodeState, SwarmSnapshot
from fcpp_bridge.metrics import MetricsCollector
from fcpp_bridge.visualization import TextDashboard, create_visualizer


def _make_snapshot(round_number: int, values: list, sim_time: float = None) -> SwarmSnapshot:
    if sim_time is None:
        sim_time = round_number * 0.1
    nodes = [NodeState(node_id=i, state_data=v, timestamp=sim_time) for i, v in enumerate(values)]
    return SwarmSnapshot(round_number=round_number, time=sim_time, nodes=nodes)


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
    collector.record(_make_snapshot(0, [1.0]))
    assert viz._round_count == 1


def test_create_visualizer_no_collector_no_attach():
    viz = create_visualizer(prefer_gui=False)
    assert isinstance(viz, TextDashboard)
    assert viz._round_count == 0
