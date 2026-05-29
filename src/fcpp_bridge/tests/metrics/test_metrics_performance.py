"""Tests for Phase 6 scaling requirements — large swarms and bounded memory."""

import tempfile
from pathlib import Path

import pytest
from fcpp_bridge.ipc import NodeState, SwarmSnapshot
from fcpp_bridge.metrics import MetricsCollector
from fcpp_bridge.compiler import ProgramCache


def test_1000_node_snapshot():
    nodes = [NodeState(node_id=i, state_data=float(i), timestamp=0.0) for i in range(1000)]
    snap = SwarmSnapshot(round_number=0, time=0.0, nodes=nodes)
    c = MetricsCollector()
    c.record(snap)
    s = c.summarize()
    assert s.avg_node_count == pytest.approx(1000.0)
    assert s.min_per_round[0] == pytest.approx(0.0)
    assert s.max_per_round[0] == pytest.approx(999.0)


def test_100_rounds_bounded_memory():
    c = MetricsCollector(history_size=100)
    for i in range(200):
        nodes = [NodeState(node_id=j, state_data=float(j), timestamp=float(i)) for j in range(50)]
        snap = SwarmSnapshot(round_number=i, time=float(i) * 0.1, nodes=nodes)
        c.record(snap)
    assert len(c) == 100


def test_compile_100_programs_cache_no_collision():
    with tempfile.TemporaryDirectory() as tmpdir:
        cache = ProgramCache(Path(tmpdir))
        keys = {cache.get_key(f"int x_{i} = {i};") for i in range(100)}
        assert len(keys) == 100  # all unique
