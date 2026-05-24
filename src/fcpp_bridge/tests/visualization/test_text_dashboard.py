"""Tests for TextDashboard — terminal visualizer."""

import io
import pytest

from fcpp_bridge.ipc import NodeState, SwarmSnapshot
from fcpp_bridge.metrics import MetricsCollector
from fcpp_bridge.visualization import TextDashboard


def _make_snapshot(round_number: int, values: list, sim_time: float = None) -> SwarmSnapshot:
    if sim_time is None:
        sim_time = round_number * 0.1
    nodes = [NodeState(node_id=i, state_data=v, timestamp=sim_time) for i, v in enumerate(values)]
    return SwarmSnapshot(round_number=round_number, time=sim_time, nodes=nodes)


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
    dash.update(_make_snapshot(42, [10.0, 20.0, 30.0]))
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
        dash.update(_make_snapshot(i, [float(i)]))
    assert dash._round_count == 5


def test_text_dashboard_replay_from_history():
    collector = MetricsCollector()
    for i in range(3):
        collector.record(_make_snapshot(i, [float(i)]))

    buf = io.StringIO()
    dash = TextDashboard(stream=buf)
    dash.replay_from_history(collector)
    lines = [ln for ln in buf.getvalue().splitlines() if ln.strip()]
    assert len(lines) == 3
