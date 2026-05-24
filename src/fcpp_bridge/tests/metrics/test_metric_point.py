"""Tests for MetricPoint dataclass."""

import pytest
from fcpp_bridge.metrics import MetricPoint


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
