"""Tests for PhysicalNode — physical device deployment mode."""

import time
import pytest
from unittest.mock import MagicMock, patch

from fcpp_bridge.ipc import PhysicalNode, SwarmSnapshot
from fcpp_bridge.ipc.node_state import NodeState


# ============================================================================
# Helpers
# ============================================================================

def _snapshot(*node_ids: int) -> SwarmSnapshot:
    nodes = [NodeState(node_id=nid, state_data={}, timestamp=0.0) for nid in node_ids]
    return SwarmSnapshot(round_number=0, time=0.0, nodes=nodes)


# ============================================================================
# 1. Construction and initial state
# ============================================================================

def test_physical_node_init_stores_params():
    node = PhysicalNode("10.0.0.1", 8080, backend_type="http", reconnect_interval=3.0)
    assert node.host == "10.0.0.1"
    assert node.port == 8080
    assert node.backend_type == "http"
    assert node.reconnect_interval == 3.0


def test_physical_node_is_connected_false_before_connect():
    node = PhysicalNode("localhost", 9000)
    assert not node.is_connected


def test_physical_node_node_count_no_snapshots_returns_one():
    node = PhysicalNode("localhost", 9000)
    assert node.node_count == 1


# ============================================================================
# 2. connect() — backend creation
# ============================================================================

def test_physical_node_connect_http_creates_http_backend():
    node = PhysicalNode("127.0.0.1", 8080, backend_type="http")
    mock_backend = MagicMock()
    with patch("fcpp_bridge.ipc.physical_node.HttpBackend", return_value=mock_backend) as mock_cls:
        node.connect()
    mock_cls.assert_called_once_with("http://127.0.0.1:8080")
    assert node.is_connected
    assert node.backend is mock_backend


def test_physical_node_connect_grpc_creates_grpc_backend():
    node = PhysicalNode("127.0.0.1", 50051, backend_type="grpc")
    mock_backend = MagicMock()
    with patch("fcpp_bridge.ipc.physical_node.GrpcBackend", return_value=mock_backend) as mock_cls:
        node.connect()
    mock_cls.assert_called_once_with(port=50051)
    assert node.is_connected


def test_physical_node_connect_invalid_backend_raises():
    node = PhysicalNode("localhost", 8080, backend_type="unix")
    with pytest.raises(ValueError, match="Unknown backend type"):
        node.connect()
    assert not node.is_connected


def test_physical_node_connect_subscribes_push_updates():
    node = PhysicalNode("127.0.0.1", 8080)
    mock_backend = MagicMock()
    with patch("fcpp_bridge.ipc.physical_node.HttpBackend", return_value=mock_backend):
        node.connect()
    mock_backend.subscribe_state_updates.assert_called_once_with(node._dispatch_update)


# ============================================================================
# 3. close()
# ============================================================================

def test_physical_node_close_sets_not_connected():
    node = PhysicalNode("127.0.0.1", 8080)
    mock_backend = MagicMock()
    with patch("fcpp_bridge.ipc.physical_node.HttpBackend", return_value=mock_backend):
        node.connect()
    assert node.is_connected
    node.close()
    assert not node.is_connected


def test_physical_node_close_calls_backend_close():
    node = PhysicalNode("127.0.0.1", 8080)
    mock_backend = MagicMock()
    with patch("fcpp_bridge.ipc.physical_node.HttpBackend", return_value=mock_backend):
        node.connect()
    node.close()
    mock_backend.close.assert_called()


def test_physical_node_close_without_connect_does_not_raise():
    node = PhysicalNode("localhost", 9000)
    node.close()  # must not raise


# ============================================================================
# 4. Context manager
# ============================================================================

def test_physical_node_context_manager():
    node = PhysicalNode("127.0.0.1", 8080)
    mock_backend = MagicMock()
    with patch("fcpp_bridge.ipc.physical_node.HttpBackend", return_value=mock_backend):
        with node:
            assert node.is_connected
    assert not node.is_connected


# ============================================================================
# 5. get_state() — inherited from _IpcNodeBase
# ============================================================================

def test_physical_node_get_state_calls_backend():
    node = PhysicalNode("127.0.0.1", 8080)
    snap = _snapshot(1, 2)
    node.backend = MagicMock()
    node.backend.get_state.return_value = snap
    result = node.get_state()
    assert result is snap


def test_physical_node_get_state_without_backend_raises():
    node = PhysicalNode("localhost", 9000)
    with pytest.raises(RuntimeError):
        node.get_state()


# ============================================================================
# 6. Listener pipeline — inherited from _IpcNodeBase
# ============================================================================

def test_physical_node_add_listener_returns_int():
    node = PhysicalNode("localhost", 9000)
    lid = node.add_listener(lambda snap: None)
    assert isinstance(lid, int)


def test_physical_node_add_node_listener_returns_int():
    node = PhysicalNode("localhost", 9000)
    lid = node.add_node_listener(42, lambda snap: None)
    assert isinstance(lid, int)


# ============================================================================
# 7. Heartbeat — inherited from _IpcNodeBase
# ============================================================================

def test_physical_node_check_liveness_after_dispatch():
    node = PhysicalNode("localhost", 9000)
    snap = _snapshot(10)
    node.backend = MagicMock()
    node._dispatch_update(snap)
    liveness = node.check_liveness(timeout=5.0)
    assert liveness[10] is True


# ============================================================================
# 8. Autonomous neighbor join
# ============================================================================

def test_physical_node_on_neighbor_joined_fires_for_new_id():
    node = PhysicalNode("localhost", 9000)
    joined = []
    node.on_neighbor_joined(joined.append)

    node.backend = MagicMock()
    node._dispatch_update(_snapshot(7))
    assert joined == [7]


def test_physical_node_on_neighbor_joined_not_fired_twice_for_same_id():
    node = PhysicalNode("localhost", 9000)
    joined = []
    node.on_neighbor_joined(joined.append)

    node.backend = MagicMock()
    node._dispatch_update(_snapshot(7))
    node._dispatch_update(_snapshot(7))  # second time — same ID
    assert joined == [7]


def test_physical_node_on_neighbor_joined_fires_for_each_unique_id():
    node = PhysicalNode("localhost", 9000)
    joined = []
    node.on_neighbor_joined(joined.append)

    node.backend = MagicMock()
    node._dispatch_update(_snapshot(1, 2))
    node._dispatch_update(_snapshot(3))
    assert set(joined) == {1, 2, 3}


def test_physical_node_node_count_reflects_seen_nodes():
    node = PhysicalNode("localhost", 9000)
    node.backend = MagicMock()
    node._dispatch_update(_snapshot(1, 2, 3))
    assert node.node_count == 3


# ============================================================================
# 9. Autonomous neighbor leave (heartbeat-driven)
# ============================================================================

def test_physical_node_on_neighbor_left_fires_via_heartbeat():
    node = PhysicalNode("localhost", 9000)
    node.backend = MagicMock()

    # First, register node 5
    node._dispatch_update(_snapshot(5))

    # Plant a stale timestamp so the heartbeat immediately sees it as dead
    node._heartbeat_timestamps[5] = time.time() - 100.0

    left = []
    node.on_neighbor_left(left.append)

    node.start_heartbeat_monitor(interval=0.05, timeout=1.0)
    time.sleep(0.2)
    node.stop_heartbeat_monitor()

    assert 5 in left


def test_physical_node_on_dead_and_neighbor_left_both_called():
    node = PhysicalNode("localhost", 9000)
    node.backend = MagicMock()

    node._dispatch_update(_snapshot(99))
    node._heartbeat_timestamps[99] = time.time() - 100.0

    left = []
    on_dead_called = []
    node.on_neighbor_left(left.append)

    node.start_heartbeat_monitor(interval=0.05, timeout=1.0, on_dead=on_dead_called.append)
    time.sleep(0.2)
    node.stop_heartbeat_monitor()

    assert 99 in left
    assert 99 in on_dead_called


# ============================================================================
# 10. Auto-reconnect
# ============================================================================

def test_physical_node_start_auto_reconnect_is_idempotent():
    node = PhysicalNode("localhost", 9000, reconnect_interval=60.0)
    node.start_auto_reconnect()
    thread_before = node._reconnect_thread
    node.start_auto_reconnect()  # second call — must reuse existing thread
    assert node._reconnect_thread is thread_before
    node.stop_auto_reconnect()


def test_physical_node_stop_auto_reconnect_clears_thread():
    node = PhysicalNode("localhost", 9000, reconnect_interval=60.0)
    node.start_auto_reconnect()
    assert node._reconnect_thread is not None
    node.stop_auto_reconnect()
    assert node._reconnect_thread is None


# ============================================================================
# 11. RAII-style connect() — Step B.3
# ============================================================================

def test_connect_raii_backend_raises_leaves_disconnected():
    """If backend constructor raises, is_connected stays False and backend is None."""
    node = PhysicalNode("localhost", 9000, backend_type="http")
    with patch("fcpp_bridge.ipc.physical_node.HttpBackend", side_effect=OSError("refused")):
        with pytest.raises(OSError):
            node.connect()
    assert not node.is_connected
    assert node.backend is None


def test_connect_raii_subscribe_raises_closes_backend():
    """If subscribe_state_updates raises, the backend is closed and is_connected stays False."""
    node = PhysicalNode("localhost", 9000, backend_type="http")
    mock_backend = MagicMock()
    mock_backend.subscribe_state_updates.side_effect = ConnectionError("no route")
    with patch("fcpp_bridge.ipc.physical_node.HttpBackend", return_value=mock_backend):
        with pytest.raises(ConnectionError):
            node.connect()
    mock_backend.close.assert_called()
    assert not node.is_connected
    assert node.backend is None


def test_get_state_transport_error_marks_disconnected():
    """get_state() catching OSError/ConnectionError sets is_connected=False."""
    node = PhysicalNode("localhost", 9000)
    mock_backend = MagicMock()
    mock_backend.get_state.side_effect = OSError("link down")
    node.backend = mock_backend
    node._connected = True
    with pytest.raises(OSError):
        node.get_state()
    assert not node.is_connected
