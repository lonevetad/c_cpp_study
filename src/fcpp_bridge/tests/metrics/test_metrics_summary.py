"""Tests for MetricsSummary — statistics over recorded rounds."""

import pytest
from fcpp_bridge.ipc import NodeState, SwarmSnapshot
from fcpp_bridge.metrics import MetricsCollector


def _make_snapshot(round_number: int, values: list, sim_time: float = None) -> SwarmSnapshot:
    if sim_time is None:
        sim_time = round_number * 0.1
    nodes = [NodeState(node_id=i, state_data=v, timestamp=sim_time) for i, v in enumerate(values)]
    return SwarmSnapshot(round_number=round_number, time=sim_time, nodes=nodes)


def test_summary_empty():
    c = MetricsCollector()
    s = c.summarize()
    assert s.total_rounds == 0
    assert s.mean_per_round == []
    assert s.avg_node_count == 0.0


def test_summary_single_round():
    c = MetricsCollector()
    c.record(_make_snapshot(0, [10.0, 20.0, 30.0]))
    s = c.summarize()
    assert s.total_rounds == 1
    assert s.mean_per_round[0] == pytest.approx(20.0)
    assert s.min_per_round[0] == pytest.approx(10.0)
    assert s.max_per_round[0] == pytest.approx(30.0)
    assert s.std_per_round[0] > 0.0


def test_summary_node_count():
    c = MetricsCollector()
    c.record(_make_snapshot(0, [1.0, 2.0, 3.0]))
    s = c.summarize()
    assert s.avg_node_count == pytest.approx(3.0)


def test_summary_multiple_rounds():
    c = MetricsCollector()
    c.record(_make_snapshot(0, [1.0, 2.0], sim_time=0.0))
    c.record(_make_snapshot(1, [3.0, 4.0], sim_time=1.0))
    s = c.summarize()
    assert s.total_rounds == 2
    assert len(s.mean_per_round) == 2
    assert s.total_sim_time == pytest.approx(1.0)


def test_summary_single_node_zero_std():
    c = MetricsCollector()
    c.record(_make_snapshot(0, [5.0]))
    s = c.summarize()
    assert s.std_per_round[0] == pytest.approx(0.0)


def test_summary_none_state_data():
    c = MetricsCollector()
    nodes = [NodeState(node_id=0, state_data=None, timestamp=0.0)]
    snap = SwarmSnapshot(round_number=0, time=0.0, nodes=nodes)
    c.record(snap)
    s = c.summarize()
    assert s.mean_per_round[0] == pytest.approx(0.0)
