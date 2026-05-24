"""Tests for StateHistory — ring-buffer of SwarmSnapshots."""

import pytest
from fcpp_bridge.ipc import NodeState, SwarmSnapshot
from fcpp_bridge.metrics import StateHistory


def _make_snapshot(round_number: int, values: list, sim_time: float = None) -> SwarmSnapshot:
    if sim_time is None:
        sim_time = round_number * 0.1
    nodes = [NodeState(node_id=i, state_data=v, timestamp=sim_time) for i, v in enumerate(values)]
    return SwarmSnapshot(round_number=round_number, time=sim_time, nodes=nodes)


def test_state_history_add_single():
    h = StateHistory()
    h.add(_make_snapshot(0, [1.0]))
    assert len(h) == 1


def test_state_history_add_multiple():
    h = StateHistory()
    for i in range(5):
        h.add(_make_snapshot(i, [float(i)]))
    assert len(h) == 5


def test_state_history_max_size_bounds():
    h = StateHistory(max_size=3)
    for i in range(7):
        h.add(_make_snapshot(i, [float(i)]))
    assert len(h) == 3


def test_state_history_max_size_keeps_latest():
    h = StateHistory(max_size=2)
    for i in range(4):
        h.add(_make_snapshot(i, [float(i)]))
    snaps = h.to_list()
    assert snaps[0].round_number == 2
    assert snaps[1].round_number == 3


def test_state_history_clear():
    h = StateHistory()
    h.add(_make_snapshot(0, [1.0]))
    h.clear()
    assert len(h) == 0


def test_state_history_get_round_positive():
    h = StateHistory()
    h.add(_make_snapshot(0, [1.0]))
    h.add(_make_snapshot(1, [2.0]))
    assert h.get_round(0).round_number == 0
    assert h.get_round(1).round_number == 1


def test_state_history_get_round_negative():
    h = StateHistory()
    h.add(_make_snapshot(0, [1.0]))
    h.add(_make_snapshot(1, [2.0]))
    assert h.get_round(-1).round_number == 1
    assert h.get_round(-2).round_number == 0


def test_state_history_to_list():
    h = StateHistory()
    h.add(_make_snapshot(0, [1.0]))
    h.add(_make_snapshot(1, [2.0]))
    lst = h.to_list()
    assert isinstance(lst, list)
    assert len(lst) == 2


def test_state_history_get_node_history_present():
    h = StateHistory()
    h.add(_make_snapshot(0, [10.0, 20.0]))
    h.add(_make_snapshot(1, [11.0, 21.0]))
    node_hist = h.get_node_history(0)
    assert len(node_hist) == 2
    assert node_hist[0].state_data == 10.0
    assert node_hist[1].state_data == 11.0


def test_state_history_get_node_history_missing_node():
    h = StateHistory()
    h.add(_make_snapshot(0, [1.0]))
    node_hist = h.get_node_history(99)
    assert node_hist == [None]
