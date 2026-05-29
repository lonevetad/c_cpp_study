"""Tests for ListenerProxy, multi-listener pipeline, node addition/removal,
and heartbeat/liveness — all new features added in the network refactor."""

import time
import threading
import pytest
from pathlib import Path
from unittest.mock import MagicMock, call

from fcpp_bridge.ipc import (
    ListenerProxy,
    SwarmProcess,
    SwarmSnapshot,
    NodeState,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _snap(round_num=0, node_ids=(0,)):
    nodes = [NodeState(node_id=nid, state_data=None, timestamp=0.0) for nid in node_ids]
    return SwarmSnapshot(round_number=round_num, time=0.0, nodes=nodes)


def _mock_swarm():
    swarm = SwarmProcess(binary_path=Path("/tmp/mock"))
    swarm.backend = MagicMock()
    swarm._known_node_ids = {0, 1, 2}
    swarm._next_sequential_id = 3
    return swarm


# ===========================================================================
# ListenerProxy — sequential mode
# ===========================================================================


def test_listener_proxy_sequential_dispatch():
    calls = []
    proxy = ListenerProxy(mode="sequential")
    proxy.add_listener(lambda s: calls.append(("a", s.round_number)))
    proxy.add_listener(lambda s: calls.append(("b", s.round_number)))
    snap = _snap(round_num=7)
    proxy(snap)
    assert calls == [("a", 7), ("b", 7)]


def test_listener_proxy_add_returns_incrementing_ids():
    proxy = ListenerProxy()
    assert proxy.add_listener(lambda s: None) == 0
    assert proxy.add_listener(lambda s: None) == 1
    assert proxy.add_listener(lambda s: None) == 2


def test_listener_proxy_remove_listener():
    received = []
    proxy = ListenerProxy()
    lid = proxy.add_listener(lambda s: received.append(s))
    proxy.remove_listener(lid)
    proxy(_snap())
    assert received == []


def test_listener_proxy_remove_unknown_id_raises():
    proxy = ListenerProxy()
    with pytest.raises(KeyError):
        proxy.remove_listener(999)


def test_listener_proxy_len():
    proxy = ListenerProxy()
    proxy.add_listener(lambda s: None)
    proxy.add_listener(lambda s: None)
    assert len(proxy) == 2


def test_listener_proxy_only_remaining_called_after_remove():
    received = []
    proxy = ListenerProxy()
    lid_a = proxy.add_listener(lambda s: received.append("a"))
    proxy.add_listener(lambda s: received.append("b"))
    proxy.remove_listener(lid_a)
    proxy(_snap())
    assert received == ["b"]


def test_listener_proxy_invalid_mode_raises():
    with pytest.raises(ValueError):
        ListenerProxy(mode="turbo")


def test_listener_proxy_mode_property():
    proxy = ListenerProxy(mode="sequential")
    assert proxy.mode == "sequential"


def test_listener_proxy_parallel_mode_dispatches():
    """Parallel mode: both listeners receive the update (may arrive async)."""
    barrier = threading.Barrier(3, timeout=2)  # 2 listeners + 1 main thread
    received = []

    def fn(_snap, tag):
        received.append(tag)
        barrier.wait()

    proxy = ListenerProxy(mode="parallel")
    proxy.add_listener(lambda s: fn(s, "a"))
    proxy.add_listener(lambda s: fn(s, "b"))
    proxy(_snap())
    barrier.wait()
    assert sorted(received) == ["a", "b"]
    proxy.close()


# ===========================================================================
# SwarmProcess — global listener management
# ===========================================================================


def test_add_listener_returns_id():
    swarm = _mock_swarm()
    lid = swarm.add_listener(lambda s: None)
    assert isinstance(lid, int)


def test_add_listener_first_call_creates_proxy():
    swarm = _mock_swarm()
    swarm.add_listener(lambda s: None)
    assert swarm._global_listener is not None
    assert isinstance(swarm._global_listener, ListenerProxy)


def test_add_two_listeners_both_called():
    swarm = _mock_swarm()
    received = []
    swarm.add_listener(lambda s: received.append("x"))
    swarm.add_listener(lambda s: received.append("y"))
    snap = _snap(node_ids=(0,))
    swarm._dispatch_update(snap)
    assert received == ["x", "y"]


def test_remove_listener():
    swarm = _mock_swarm()
    received = []
    lid = swarm.add_listener(lambda s: received.append(1))
    swarm.add_listener(lambda s: received.append(2))
    swarm.remove_listener(lid)
    swarm._dispatch_update(_snap(node_ids=(0,)))
    assert received == [2]


def test_remove_listener_no_proxy_raises():
    swarm = _mock_swarm()
    with pytest.raises(RuntimeError):
        swarm.remove_listener(0)


# ===========================================================================
# SwarmProcess — per-node listener overrides global
# ===========================================================================


def test_per_node_listener_overrides_global():
    swarm = _mock_swarm()
    global_calls = []
    node_calls = []
    swarm.add_listener(lambda s: global_calls.append(s))
    swarm.add_node_listener(1, lambda s: node_calls.append(s))

    # Snapshot with two nodes: node 0 → global; node 1 → per-node override
    snap = _snap(node_ids=(0, 1))
    swarm._dispatch_update(snap)

    assert len(global_calls) == 1    # node 0 only
    assert len(node_calls) == 1      # node 1 only


def test_add_node_listener_returns_id():
    swarm = _mock_swarm()
    lid = swarm.add_node_listener(0, lambda s: None)
    assert isinstance(lid, int)


def test_remove_node_listener():
    swarm = _mock_swarm()
    received = []
    lid = swarm.add_node_listener(0, lambda s: received.append(1))
    swarm.remove_node_listener(0, lid)
    swarm._dispatch_update(_snap(node_ids=(0,)))
    assert received == []


def test_remove_node_listener_no_proxy_raises():
    swarm = _mock_swarm()
    with pytest.raises(RuntimeError):
        swarm.remove_node_listener(99, 0)


# ===========================================================================
# SwarmProcess — node addition strategies
# ===========================================================================


def test_add_nodes_sequential_returns_sequential_ids():
    swarm = _mock_swarm()
    ids = swarm.add_nodes_sequential(3)
    assert ids == [3, 4, 5]
    assert swarm._next_sequential_id == 6


def test_add_nodes_sequential_updates_num_nodes():
    swarm = _mock_swarm()
    swarm.add_nodes_sequential(2)
    assert swarm.num_nodes == 102


def test_add_nodes_sequential_with_positions():
    swarm = _mock_swarm()
    swarm.add_nodes_sequential(2, start_positions=[(1.0, 2.0), (3.0, 4.0)])
    cmd = swarm.backend.send_command.call_args[0][0]
    assert cmd["nodes"][0]["position"] == [1.0, 2.0]
    assert cmd["nodes"][1]["position"] == [3.0, 4.0]


def test_add_nodes_random_returns_unique_ids():
    swarm = _mock_swarm()
    ids = swarm.add_nodes_random(5)
    assert len(ids) == 5
    assert len(set(ids)) == 5  # all unique


def test_add_nodes_random_adds_to_known():
    swarm = _mock_swarm()
    ids = swarm.add_nodes_random(3)
    for nid in ids:
        assert nid in swarm._known_node_ids


def test_add_nodes_random_updates_num_nodes():
    swarm = _mock_swarm()
    swarm.add_nodes_random(4)
    assert swarm.num_nodes == 104


def test_add_node_explicit_registers_id():
    swarm = _mock_swarm()
    swarm.add_node_explicit(999, (10.0, 20.0))
    assert 999 in swarm._known_node_ids
    assert swarm.num_nodes == 101


def test_add_node_explicit_sends_correct_cmd():
    swarm = _mock_swarm()
    swarm.add_node_explicit(42, (5.0, 6.0), comm_range=100.0)
    cmd = swarm.backend.send_command.call_args[0][0]
    assert cmd["cmd"] == "add_node"
    assert cmd["id"] == 42
    assert cmd["position"] == [5.0, 6.0]
    assert cmd["comm_range"] == 100.0


def test_add_node_explicit_duplicate_raises():
    swarm = _mock_swarm()
    with pytest.raises(ValueError, match="already in use"):
        swarm.add_node_explicit(0, (0.0, 0.0))  # ID 0 is in _known_node_ids


def test_add_nodes_backward_compat():
    swarm = _mock_swarm()
    swarm.add_nodes(5)
    assert swarm.num_nodes == 105
    swarm.backend.send_command.assert_called_once()


# ===========================================================================
# SwarmProcess — node removal
# ===========================================================================


def test_remove_node_removes_from_known():
    swarm = _mock_swarm()
    swarm.remove_node(1)
    assert 1 not in swarm._known_node_ids


def test_remove_node_decrements_num_nodes():
    swarm = _mock_swarm()
    swarm.remove_node(0)
    assert swarm.num_nodes == 99


def test_remove_node_unknown_raises():
    swarm = _mock_swarm()
    with pytest.raises(ValueError, match="not tracked"):
        swarm.remove_node(9999)


def test_remove_node_clears_heartbeat():
    swarm = _mock_swarm()
    swarm._heartbeat_timestamps[1] = time.time()
    swarm.remove_node(1)
    assert 1 not in swarm._heartbeat_timestamps


# ===========================================================================
# SwarmProcess — liveness / heartbeat
# ===========================================================================


def test_check_liveness_fresh_node_is_alive():
    swarm = _mock_swarm()
    swarm._heartbeat_timestamps[0] = time.time()
    liveness = swarm.check_liveness(timeout=30.0)
    assert liveness[0] is True


def test_check_liveness_stale_node_is_dead():
    swarm = _mock_swarm()
    swarm._heartbeat_timestamps[0] = time.time() - 60.0  # 60 s ago
    liveness = swarm.check_liveness(timeout=30.0)
    assert liveness[0] is False


def test_get_state_updates_heartbeat():
    swarm = _mock_swarm()
    snap = _snap(node_ids=(0, 1))
    swarm.backend.get_state.return_value = snap
    before = time.time()
    swarm.get_state()
    assert 0 in swarm._heartbeat_timestamps
    assert swarm._heartbeat_timestamps[0] >= before


def test_heartbeat_monitor_calls_on_dead():
    swarm = _mock_swarm()
    swarm._heartbeat_timestamps[5] = time.time() - 100.0  # stale
    dead_nodes = []
    swarm.start_heartbeat_monitor(interval=0.05, timeout=10.0, on_dead=dead_nodes.append)
    time.sleep(0.15)
    swarm.stop_heartbeat_monitor()
    assert 5 in dead_nodes


def test_heartbeat_monitor_stop():
    swarm = _mock_swarm()
    swarm.start_heartbeat_monitor(interval=0.1, timeout=30.0)
    swarm.stop_heartbeat_monitor()
    assert swarm._heartbeat_thread is None


def test_heartbeat_monitor_idempotent_start():
    swarm = _mock_swarm()
    swarm.start_heartbeat_monitor(interval=0.5, timeout=30.0)
    first_thread = swarm._heartbeat_thread
    swarm.start_heartbeat_monitor(interval=0.5, timeout=30.0)  # second call
    assert swarm._heartbeat_thread is first_thread
    swarm.stop_heartbeat_monitor()
