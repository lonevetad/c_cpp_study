"""Tests for export_json and export_csv."""

import csv
import json
import tempfile
from pathlib import Path

import pytest
from fcpp_bridge.ipc import NodeState, SwarmSnapshot
from fcpp_bridge.metrics import MetricsCollector


def _make_snapshot(round_number: int, values: list, sim_time: float = None) -> SwarmSnapshot:
    if sim_time is None:
        sim_time = round_number * 0.1
    nodes = [NodeState(node_id=i, state_data=v, timestamp=sim_time) for i, v in enumerate(values)]
    return SwarmSnapshot(round_number=round_number, time=sim_time, nodes=nodes)


def test_export_json_structure():
    with tempfile.TemporaryDirectory() as tmpdir:
        c = MetricsCollector()
        for i in range(3):
            c.record(_make_snapshot(i, [float(i * 10)]))

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
        c.record(_make_snapshot(0, [1.0, 2.0]))
        c.record(_make_snapshot(1, [3.0, 4.0]))

        out = Path(tmpdir) / "metrics.csv"
        c.export_csv(out)

        assert out.exists()
        rows = list(csv.reader(open(out)))
        assert rows[0] == ["round", "sim_time", "wall_clock", "node_count", "mean", "min", "max"]
        assert len(rows) == 3  # header + 2 data rows
        assert rows[1][0] == "0"
        assert rows[2][0] == "1"
