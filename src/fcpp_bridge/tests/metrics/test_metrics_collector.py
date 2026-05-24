"""Tests for MetricsCollector — recording, callbacks, custom extractor."""

import pytest
from fcpp_bridge.ipc import NodeState, SwarmSnapshot
from fcpp_bridge.metrics import MetricsCollector


def _make_snapshot(round_number: int, values: list, sim_time: float = None) -> SwarmSnapshot:
    if sim_time is None:
        sim_time = round_number * 0.1
    nodes = [NodeState(node_id=i, state_data=v, timestamp=sim_time) for i, v in enumerate(values)]
    return SwarmSnapshot(round_number=round_number, time=sim_time, nodes=nodes)


# ============================================================================
# Test 3: Basic recording
# ============================================================================


def test_collector_record_one():
    c = MetricsCollector()
    c.record(_make_snapshot(0, [1.0, 2.0]))
    assert len(c) == 1


def test_collector_record_many():
    c = MetricsCollector()
    for i in range(20):
        c.record(_make_snapshot(i, [float(i)] * 3))
    assert len(c) == 20


def test_collector_history_size_limit():
    c = MetricsCollector(history_size=5)
    for i in range(12):
        c.record(_make_snapshot(i, [float(i)]))
    assert len(c) == 5


def test_collector_clear():
    c = MetricsCollector()
    c.record(_make_snapshot(0, [1.0]))
    c.clear()
    assert len(c) == 0


# ============================================================================
# Test 4: Callbacks
# ============================================================================


def test_collector_callback_fires():
    c = MetricsCollector()
    received = []
    c.on_update(received.append)
    snap = _make_snapshot(0, [1.0])
    c.record(snap)
    assert len(received) == 1
    assert received[0] is snap


def test_collector_multiple_callbacks():
    c = MetricsCollector()
    counts = [0, 0]
    c.on_update(lambda s: counts.__setitem__(0, counts[0] + 1))
    c.on_update(lambda s: counts.__setitem__(1, counts[1] + 1))
    c.record(_make_snapshot(0, [1.0]))
    assert counts == [1, 1]


def test_collector_remove_callback():
    c = MetricsCollector()
    count = [0]

    def cb(s):
        count[0] += 1

    c.on_update(cb)
    c.remove_callback(cb)
    c.record(_make_snapshot(0, [1.0]))
    assert count[0] == 0


def test_collector_remove_nonexistent_callback_noop():
    c = MetricsCollector()
    c.remove_callback(lambda s: None)  # should not raise


# ============================================================================
# Test 5: Custom extractor
# ============================================================================


def test_collector_custom_extractor():
    c = MetricsCollector(state_extractor=lambda n: n.state_data * 2.0)
    c.record(_make_snapshot(0, [3.0, 4.0]))
    s = c.summarize()
    assert s.mean_per_round[0] == pytest.approx(7.0)  # mean of [6.0, 8.0]


def test_collector_bad_extractor_graceful():
    def bad(n):
        raise ValueError("intentional")

    c = MetricsCollector(state_extractor=bad)
    c.record(_make_snapshot(0, [1.0, 2.0]))  # must not raise
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
