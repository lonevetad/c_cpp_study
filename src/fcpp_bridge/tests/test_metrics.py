"""Tests for Phase 6 — Metrics Collection & Scaling."""

import json
import csv
import tempfile
import pytest
from pathlib import Path

from fcpp_bridge.ipc import NodeState, SwarmSnapshot
from fcpp_bridge.metrics import (
    MetricPoint,
    MetricsSummary,
    StateHistory,
    MetricsCollector,
)


# ============================================================================
# Helpers
# ============================================================================


def make_snapshot(
    round_number: int,
    values: list,
    sim_time: float = None,
) -> SwarmSnapshot:
    if sim_time is None:
        sim_time = round_number * 0.1
    nodes = [
        NodeState(node_id=i, state_data=v, timestamp=sim_time)
        for i, v in enumerate(values)
    ]
    return SwarmSnapshot(round_number=round_number, time=sim_time, nodes=nodes)


# ============================================================================
# Test 1: MetricPoint
# ============================================================================


def test_metric_point_creation():
    p = MetricPoint(
        round_number=1, sim_time=0.1, wall_clock=100.0,
        node_count=5, numeric_values=[1.0, 2.0, 3.0],
    )
    assert p.round_number == 1
    assert p.node_count == 5
    assert len(p.numeric_values) == 3


def test_metric_point_empty_values():
    p = MetricPoint(round_number=0, sim_time=0.0, wall_clock=0.0, node_count=0, numeric_values=[])
    assert p.numeric_values == []


# ============================================================================
# Test 2: StateHistory
# ============================================================================


def test_state_history_add_single():
    h = StateHistory()
    h.add(make_snapshot(0, [1.0]))
    assert len(h) == 1


def test_state_history_add_multiple():
    h = StateHistory()
    for i in range(5):
        h.add(make_snapshot(i, [float(i)]))
    assert len(h) == 5


def test_state_history_max_size_bounds():
    h = StateHistory(max_size=3)
    for i in range(7):
        h.add(make_snapshot(i, [float(i)]))
    assert len(h) == 3


def test_state_history_max_size_keeps_latest():
    h = StateHistory(max_size=2)
    for i in range(4):
        h.add(make_snapshot(i, [float(i)]))
    snaps = h.to_list()
    assert snaps[0].round_number == 2
    assert snaps[1].round_number == 3


def test_state_history_clear():
    h = StateHistory()
    h.add(make_snapshot(0, [1.0]))
    h.clear()
    assert len(h) == 0


def test_state_history_get_round_positive():
    h = StateHistory()
    h.add(make_snapshot(0, [1.0]))
    h.add(make_snapshot(1, [2.0]))
    assert h.get_round(0).round_number == 0
    assert h.get_round(1).round_number == 1


def test_state_history_get_round_negative():
    h = StateHistory()
    h.add(make_snapshot(0, [1.0]))
    h.add(make_snapshot(1, [2.0]))
    assert h.get_round(-1).round_number == 1
    assert h.get_round(-2).round_number == 0


def test_state_history_to_list():
    h = StateHistory()
    h.add(make_snapshot(0, [1.0]))
    h.add(make_snapshot(1, [2.0]))
    lst = h.to_list()
    assert isinstance(lst, list)
    assert len(lst) == 2


def test_state_history_get_node_history_present():
    h = StateHistory()
    h.add(make_snapshot(0, [10.0, 20.0]))
    h.add(make_snapshot(1, [11.0, 21.0]))
    node_hist = h.get_node_history(0)
    assert len(node_hist) == 2
    assert node_hist[0].state_data == 10.0
    assert node_hist[1].state_data == 11.0


def test_state_history_get_node_history_missing_node():
    h = StateHistory()
    h.add(make_snapshot(0, [1.0]))   # only node 0 exists
    node_hist = h.get_node_history(99)
    assert node_hist == [None]


# ============================================================================
# Test 3: MetricsCollector — basic recording
# ============================================================================


def test_collector_record_one():
    c = MetricsCollector()
    c.record(make_snapshot(0, [1.0, 2.0]))
    assert len(c) == 1


def test_collector_record_many():
    c = MetricsCollector()
    for i in range(20):
        c.record(make_snapshot(i, [float(i)] * 3))
    assert len(c) == 20


def test_collector_history_size_limit():
    c = MetricsCollector(history_size=5)
    for i in range(12):
        c.record(make_snapshot(i, [float(i)]))
    assert len(c) == 5


def test_collector_clear():
    c = MetricsCollector()
    c.record(make_snapshot(0, [1.0]))
    c.clear()
    assert len(c) == 0


# ============================================================================
# Test 4: MetricsCollector — callbacks
# ============================================================================


def test_collector_callback_fires():
    c = MetricsCollector()
    received = []
    c.on_update(received.append)
    snap = make_snapshot(0, [1.0])
    c.record(snap)
    assert len(received) == 1
    assert received[0] is snap


def test_collector_multiple_callbacks():
    c = MetricsCollector()
    counts = [0, 0]
    c.on_update(lambda s: counts.__setitem__(0, counts[0] + 1))
    c.on_update(lambda s: counts.__setitem__(1, counts[1] + 1))
    c.record(make_snapshot(0, [1.0]))
    assert counts == [1, 1]


def test_collector_remove_callback():
    c = MetricsCollector()
    count = [0]

    def cb(s):
        count[0] += 1

    c.on_update(cb)
    c.remove_callback(cb)
    c.record(make_snapshot(0, [1.0]))
    assert count[0] == 0


def test_collector_remove_nonexistent_callback_noop():
    c = MetricsCollector()
    c.remove_callback(lambda s: None)  # should not raise


# ============================================================================
# Test 5: MetricsCollector — custom extractor
# ============================================================================


def test_collector_custom_extractor():
    c = MetricsCollector(state_extractor=lambda n: n.state_data * 2.0)
    c.record(make_snapshot(0, [3.0, 4.0]))
    s = c.summarize()
    assert s.mean_per_round[0] == pytest.approx(7.0)  # mean of [6.0, 8.0]


def test_collector_bad_extractor_graceful():
    def bad(n):
        raise ValueError("intentional")

    c = MetricsCollector(state_extractor=bad)
    c.record(make_snapshot(0, [1.0, 2.0]))  # must not raise
    assert len(c) == 1


def test_collector_dict_state_extractor():
    c = MetricsCollector(state_extractor=lambda n: n.state_data["v"])
    nodes = [
        NodeState(node_id=i, state_data={"v": float(i * 10)}, timestamp=0.0)
        for i in range(3)
    ]
    snap = SwarmSnapshot(round_number=0, time=0.0, nodes=nodes)
    c.record(snap)
    s = c.summarize()
    assert s.mean_per_round[0] == pytest.approx(10.0)  # mean of [0, 10, 20]


# ============================================================================
# Test 6: MetricsSummary
# ============================================================================


def test_summary_empty():
    c = MetricsCollector()
    s = c.summarize()
    assert s.total_rounds == 0
    assert s.mean_per_round == []
    assert s.avg_node_count == 0.0


def test_summary_single_round():
    c = MetricsCollector()
    c.record(make_snapshot(0, [10.0, 20.0, 30.0]))
    s = c.summarize()
    assert s.total_rounds == 1
    assert s.mean_per_round[0] == pytest.approx(20.0)
    assert s.min_per_round[0] == pytest.approx(10.0)
    assert s.max_per_round[0] == pytest.approx(30.0)
    assert s.std_per_round[0] > 0.0


def test_summary_node_count():
    c = MetricsCollector()
    c.record(make_snapshot(0, [1.0, 2.0, 3.0]))  # 3 nodes
    s = c.summarize()
    assert s.avg_node_count == pytest.approx(3.0)


def test_summary_multiple_rounds():
    c = MetricsCollector()
    c.record(make_snapshot(0, [1.0, 2.0], sim_time=0.0))
    c.record(make_snapshot(1, [3.0, 4.0], sim_time=1.0))
    s = c.summarize()
    assert s.total_rounds == 2
    assert len(s.mean_per_round) == 2
    assert s.total_sim_time == pytest.approx(1.0)


def test_summary_single_node_zero_std():
    c = MetricsCollector()
    c.record(make_snapshot(0, [5.0]))
    s = c.summarize()
    assert s.std_per_round[0] == pytest.approx(0.0)


def test_summary_none_state_data():
    c = MetricsCollector()
    nodes = [NodeState(node_id=0, state_data=None, timestamp=0.0)]
    snap = SwarmSnapshot(round_number=0, time=0.0, nodes=nodes)
    c.record(snap)
    s = c.summarize()
    assert s.mean_per_round[0] == pytest.approx(0.0)


# ============================================================================
# Test 7: Export
# ============================================================================


def test_export_json_structure():
    with tempfile.TemporaryDirectory() as tmpdir:
        c = MetricsCollector()
        for i in range(3):
            c.record(make_snapshot(i, [float(i * 10)]))

        out = Path(tmpdir) / "metrics.json"
        c.export_json(out)

        assert out.exists()
        data = json.loads(out.read_text())
        assert "rounds" in data
        assert len(data["rounds"]) == 3
        assert data["rounds"][0]["round"] == 0
        assert data["rounds"][0]["node_count"] == 1


def test_export_json_empty():
    with tempfile.TemporaryDirectory() as tmpdir:
        c = MetricsCollector()
        out = Path(tmpdir) / "empty.json"
        c.export_json(out)
        data = json.loads(out.read_text())
        assert data["rounds"] == []


def test_export_csv_structure():
    with tempfile.TemporaryDirectory() as tmpdir:
        c = MetricsCollector()
        c.record(make_snapshot(0, [1.0, 2.0]))
        c.record(make_snapshot(1, [3.0, 4.0]))

        out = Path(tmpdir) / "metrics.csv"
        c.export_csv(out)

        assert out.exists()
        rows = list(csv.reader(open(out)))
        assert rows[0] == ["round", "sim_time", "wall_clock", "node_count", "mean", "min", "max"]
        assert len(rows) == 3  # header + 2 data rows
        assert rows[1][0] == "0"
        assert rows[2][0] == "1"


# ============================================================================
# Test 8: Phase 6 scaling requirements
# ============================================================================


def test_1000_node_snapshot():
    """Phase 6: handle 1000-node swarms without error."""
    nodes = [NodeState(node_id=i, state_data=float(i), timestamp=0.0) for i in range(1000)]
    snap = SwarmSnapshot(round_number=0, time=0.0, nodes=nodes)

    c = MetricsCollector()
    c.record(snap)

    s = c.summarize()
    assert s.avg_node_count == pytest.approx(1000.0)
    assert s.min_per_round[0] == pytest.approx(0.0)
    assert s.max_per_round[0] == pytest.approx(999.0)


def test_100_rounds_bounded_memory():
    """Phase 6: history_size=100 keeps exactly 100 entries even after 200 rounds."""
    c = MetricsCollector(history_size=100)
    for i in range(200):
        nodes = [NodeState(node_id=j, state_data=float(j), timestamp=float(i)) for j in range(50)]
        snap = SwarmSnapshot(round_number=i, time=float(i) * 0.1, nodes=nodes)
        c.record(snap)

    assert len(c) == 100


def test_compile_100_programs_cache_no_collision():
    """Phase 6: 100 distinct cache keys produce no collisions."""
    from fcpp_bridge.compiler import ProgramCache

    with tempfile.TemporaryDirectory() as tmpdir:
        cache = ProgramCache(Path(tmpdir))
        keys = set()
        for i in range(100):
            code = f"int x_{i} = {i};"
            keys.add(cache.get_key(code))

        assert len(keys) == 100  # all unique


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
