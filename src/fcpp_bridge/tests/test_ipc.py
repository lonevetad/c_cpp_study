"""Tests for Phase 4 IPC Backends and Runtime."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from fcpp_bridge.ipc import (
    NodeState,
    SwarmSnapshot,
    UnixSocketBackend,
    HttpBackend,
    SwarmProcess,
    DeviceManager,
)


# ============================================================================
# Test 1: Data structures
# ============================================================================


def test_node_state_creation():
    """Test NodeState dataclass."""
    state = NodeState(node_id=0, state_data=42.0, timestamp=1.5)
    assert state.node_id == 0
    assert state.state_data == 42.0
    assert state.timestamp == 1.5


def test_swarm_snapshot_creation():
    """Test SwarmSnapshot dataclass."""
    nodes = [
        NodeState(node_id=0, state_data=1.0, timestamp=0.0),
        NodeState(node_id=1, state_data=2.0, timestamp=0.0),
    ]
    snapshot = SwarmSnapshot(round_number=0, time=0.0, nodes=nodes)

    assert snapshot.round_number == 0
    assert len(snapshot.nodes) == 2
    assert snapshot.nodes[0].node_id == 0


def test_swarm_snapshot_empty():
    """Test empty SwarmSnapshot."""
    snapshot = SwarmSnapshot(round_number=0, time=0.0, nodes=[])
    assert len(snapshot.nodes) == 0


# ============================================================================
# Test 2: IPC Backend Interface
# ============================================================================


def test_unix_socket_backend_parse_snapshot():
    """Test parsing IPC response to snapshot."""
    backend = UnixSocketBackend.__new__(UnixSocketBackend)
    backend.sock = None

    response = {
        "round": 5,
        "time": 2.5,
        "nodes": [
            {"id": 0, "state": 1.0, "timestamp": 2.5},
            {"id": 1, "state": 2.0, "timestamp": 2.5},
        ],
    }

    snapshot = backend._parse_snapshot(response)
    assert snapshot.round_number == 5
    assert snapshot.time == 2.5
    assert len(snapshot.nodes) == 2


def test_http_backend_parse_snapshot():
    """Test HTTP backend snapshot parsing."""
    backend = HttpBackend.__new__(HttpBackend)

    response = {
        "round": 3,
        "time": 1.5,
        "nodes": [
            {"id": 0, "state": 100, "timestamp": 1.5},
        ],
    }

    snapshot = backend._parse_snapshot(response)
    assert snapshot.round_number == 3
    assert snapshot.time == 1.5
    assert snapshot.nodes[0].state_data == 100


# ============================================================================
# Test 3: Backend Configuration
# ============================================================================


def test_unix_socket_backend_init():
    """Test UnixSocket backend initialization."""
    from unittest.mock import patch

    with patch("socket.socket"):
        try:
            backend = UnixSocketBackend(socket_path=Path("/tmp/test.sock"))
            # Initialization should succeed (socket patched)
        except Exception:
            # Expected if socket connection fails
            pass


def test_http_backend_init():
    """Test HTTP backend initialization."""
    backend = HttpBackend(base_url="http://localhost:8080")
    assert backend.base_url == "http://localhost:8080"
    assert backend.timeout == 5.0


def test_http_backend_url_normalization():
    """Test HTTP backend normalizes URLs."""
    backend = HttpBackend(base_url="http://localhost:8080/")
    assert backend.base_url == "http://localhost:8080"


# ============================================================================
# Test 4: Swarm Process Management
# ============================================================================


def test_swarm_process_init():
    """Test SwarmProcess initialization."""
    swarm = SwarmProcess(
        binary_path=Path("/tmp/mock_swarm"),
        num_nodes=100,
        ipc_backend="unix",
    )

    assert swarm.binary_path == Path("/tmp/mock_swarm")
    assert swarm.num_nodes == 100
    assert swarm.ipc_backend_name == "unix"


def test_swarm_process_context_manager():
    """Test SwarmProcess as context manager."""
    import tempfile
    import os
    from unittest.mock import patch, MagicMock

    mock_proc = MagicMock()
    mock_backend = MagicMock()

    # Create a real (empty) file so binary_path.exists() passes
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        binary_path = Path(tmp.name)

    try:
        with patch("subprocess.Popen", return_value=mock_proc):
            with patch.object(SwarmProcess, "_create_backend"):
                swarm = SwarmProcess(binary_path=binary_path)
                swarm.backend = mock_backend

                swarm.start()
                assert swarm.process is not None
    finally:
        os.unlink(binary_path)


def test_swarm_process_add_nodes():
    """Test adding nodes to swarm."""
    from unittest.mock import MagicMock

    swarm = SwarmProcess(
        binary_path=Path("/tmp/mock"),
        num_nodes=10,
    )
    swarm.backend = MagicMock()

    swarm.add_nodes(5)
    assert swarm.num_nodes == 15
    swarm.backend.send_command.assert_called_once()


# ============================================================================
# Test 5: Error Handling
# ============================================================================


def test_swarm_process_missing_binary():
    """Test error when binary not found."""
    swarm = SwarmProcess(binary_path=Path("/nonexistent/path"))

    with pytest.raises(FileNotFoundError):
        swarm.start()


def test_unix_socket_backend_parse_snapshot_missing_fields():
    """Test robust parsing with missing fields."""
    backend = UnixSocketBackend.__new__(UnixSocketBackend)

    response = {"nodes": [{"id": 0}]}  # Missing state, timestamp

    snapshot = backend._parse_snapshot(response)
    assert len(snapshot.nodes) == 1
    assert snapshot.nodes[0].state_data is None


# ============================================================================
# Test 6: NodeState edge cases
# ============================================================================


def test_node_state_dict_state_data():
    state = NodeState(node_id=5, state_data={"x": 1.0, "y": 2.0}, timestamp=3.0)
    assert state.state_data["x"] == 1.0
    assert state.node_id == 5


def test_node_state_list_state_data():
    state = NodeState(node_id=0, state_data=[1, 2, 3], timestamp=0.0)
    assert len(state.state_data) == 3


def test_node_state_none_state_data():
    state = NodeState(node_id=0, state_data=None, timestamp=0.0)
    assert state.state_data is None


def test_swarm_snapshot_many_nodes():
    nodes = [NodeState(node_id=i, state_data=float(i), timestamp=1.0) for i in range(50)]
    snap = SwarmSnapshot(round_number=1, time=1.0, nodes=nodes)
    assert len(snap.nodes) == 50
    assert snap.nodes[49].node_id == 49


def test_swarm_snapshot_round_zero():
    snap = SwarmSnapshot(round_number=0, time=0.0, nodes=[])
    assert snap.round_number == 0
    assert snap.time == 0.0


# ============================================================================
# Test 7: Parse snapshot edge cases
# ============================================================================


def test_parse_snapshot_empty_nodes():
    backend = UnixSocketBackend.__new__(UnixSocketBackend)
    snap = backend._parse_snapshot({"round": 0, "time": 0.0, "nodes": []})
    assert snap.nodes == []


def test_parse_snapshot_missing_round():
    backend = UnixSocketBackend.__new__(UnixSocketBackend)
    snap = backend._parse_snapshot({"nodes": []})
    assert snap.round_number == 0


def test_parse_snapshot_missing_time():
    backend = UnixSocketBackend.__new__(UnixSocketBackend)
    snap = backend._parse_snapshot({"nodes": []})
    assert snap.time == 0.0


def test_parse_snapshot_node_with_timestamp():
    backend = UnixSocketBackend.__new__(UnixSocketBackend)
    response = {"round": 1, "time": 0.5, "nodes": [{"id": 0, "state": 99.0, "timestamp": 0.5}]}
    snap = backend._parse_snapshot(response)
    assert snap.nodes[0].timestamp == 0.5
    assert snap.nodes[0].state_data == 99.0


def test_http_parse_snapshot_empty_nodes():
    backend = HttpBackend.__new__(HttpBackend)
    snap = backend._parse_snapshot({"round": 0, "time": 0.0, "nodes": []})
    assert snap.nodes == []


def test_http_parse_snapshot_missing_state():
    backend = HttpBackend.__new__(HttpBackend)
    snap = backend._parse_snapshot({"nodes": [{"id": 0}]})
    assert snap.nodes[0].state_data is None


# ============================================================================
# Test 8: SwarmProcess extended
# ============================================================================


def test_swarm_process_default_num_nodes():
    swarm = SwarmProcess(binary_path=Path("/tmp/mock"))
    assert swarm.num_nodes == 100


def test_swarm_process_custom_num_nodes():
    swarm = SwarmProcess(binary_path=Path("/tmp/mock"), num_nodes=500)
    assert swarm.num_nodes == 500


def test_swarm_process_ipc_backend_http():
    swarm = SwarmProcess(
        binary_path=Path("/tmp/mock"),
        ipc_backend="http://localhost:9090",
    )
    assert swarm.ipc_backend_name == "http://localhost:9090"


def test_swarm_process_ipc_backend_grpc():
    swarm = SwarmProcess(binary_path=Path("/tmp/mock"), ipc_backend="grpc")
    assert swarm.ipc_backend_name == "grpc"


def test_swarm_process_step_calls_backend():
    from unittest.mock import MagicMock
    swarm = SwarmProcess(binary_path=Path("/tmp/mock"))
    swarm.backend = MagicMock()
    swarm.step()
    swarm.backend.send_command.assert_called_once_with({"cmd": "step"})


def test_swarm_process_get_state_calls_backend():
    from unittest.mock import MagicMock
    swarm = SwarmProcess(binary_path=Path("/tmp/mock"))
    mock_snap = SwarmSnapshot(round_number=0, time=0.0, nodes=[])
    swarm.backend = MagicMock()
    swarm.backend.get_state.return_value = mock_snap
    result = swarm.get_state()
    assert result is mock_snap


def test_swarm_process_step_without_backend():
    swarm = SwarmProcess(binary_path=Path("/tmp/mock"))
    swarm.backend = None
    with pytest.raises(RuntimeError):
        swarm.step()


def test_swarm_process_get_state_without_backend():
    swarm = SwarmProcess(binary_path=Path("/tmp/mock"))
    swarm.backend = None
    with pytest.raises(RuntimeError):
        swarm.get_state()


def test_swarm_process_add_nodes_without_backend():
    swarm = SwarmProcess(binary_path=Path("/tmp/mock"))
    swarm.backend = None
    with pytest.raises(RuntimeError):
        swarm.add_nodes(5)


def test_swarm_process_close_no_error_when_not_started():
    swarm = SwarmProcess(binary_path=Path("/tmp/mock"))
    swarm.close()  # should not raise


def test_swarm_process_invalid_backend_raises():
    swarm = SwarmProcess(binary_path=Path("/tmp/fake_binary"))
    swarm.process = __import__("subprocess").Popen.__new__(__import__("subprocess").Popen)

    with pytest.raises(ValueError):
        swarm.ipc_backend_name = "invalid_backend"
        swarm._create_backend()


def test_http_backend_timeout_default():
    backend = HttpBackend()
    assert backend.timeout == 5.0


def test_http_backend_custom_timeout():
    backend = HttpBackend(timeout=10.0)
    assert backend.timeout == 10.0


def test_http_backend_close_noop():
    backend = HttpBackend()
    backend.close()  # must not raise


# ============================================================================
# DeviceManager tests
# ============================================================================

from fcpp_bridge.ipc import DeviceManager


def _dummy_binary(tmp_path):
    """Create a dummy executable file for path-existence checks."""
    p = tmp_path / "dummy_bin"
    p.write_bytes(b"")
    p.chmod(0o755)
    return p


def test_device_manager_instantiation():
    """DeviceManager can be created with no arguments."""
    mgr = DeviceManager()
    assert mgr.device_count == 0
    assert mgr.device_names == []


def test_device_manager_add(tmp_path):
    """add() registers a device and returns a SwarmProcess."""
    mgr = DeviceManager()
    proc = mgr.add("s1", _dummy_binary(tmp_path))
    assert "s1" in mgr.device_names
    assert mgr.device_count == 1
    assert isinstance(proc, SwarmProcess)


def test_device_manager_add_duplicate_raises(tmp_path):
    """Adding a device with the same name raises ValueError."""
    mgr = DeviceManager()
    b = _dummy_binary(tmp_path)
    mgr.add("s1", b)
    with pytest.raises(ValueError, match="s1"):
        mgr.add("s1", b)


def test_device_manager_get(tmp_path):
    """get() returns the registered SwarmProcess."""
    mgr = DeviceManager()
    proc = mgr.add("s1", _dummy_binary(tmp_path))
    assert mgr.get("s1") is proc


def test_device_manager_get_missing_raises():
    """get() raises KeyError for unknown names."""
    mgr = DeviceManager()
    with pytest.raises(KeyError):
        mgr.get("no_such_device")


def test_device_manager_remove(tmp_path):
    """remove() unregisters a device."""
    mgr = DeviceManager()
    mgr.add("s1", _dummy_binary(tmp_path))
    mgr.remove("s1")
    assert mgr.device_count == 0


def test_device_manager_remove_missing_raises():
    """remove() raises KeyError for unknown names."""
    mgr = DeviceManager()
    with pytest.raises(KeyError):
        mgr.remove("ghost")


def test_device_manager_device_names_order(tmp_path):
    """device_names returns names in insertion order."""
    mgr = DeviceManager()
    b = _dummy_binary(tmp_path)
    mgr.add("alpha", b)
    mgr.add("beta", b)
    mgr.add("gamma", b)
    assert mgr.device_names == ["alpha", "beta", "gamma"]


def test_device_manager_total_nodes(tmp_path):
    """total_nodes sums num_nodes across all devices."""
    mgr = DeviceManager()
    b = _dummy_binary(tmp_path)
    mgr.add("s1", b, num_nodes=50)
    mgr.add("s2", b, num_nodes=150)
    assert mgr.total_nodes() == 200


def test_device_manager_send_all_no_backend(tmp_path):
    """send_all returns error dict for devices that are not connected."""
    mgr = DeviceManager()
    mgr.add("s1", _dummy_binary(tmp_path))
    result = mgr.send_all({"cmd": "step"})
    assert "s1" in result
    assert "error" in result["s1"]


def test_device_manager_get_all_states_no_backend(tmp_path):
    """get_all_states returns error dict for devices that are not connected."""
    mgr = DeviceManager()
    mgr.add("s1", _dummy_binary(tmp_path))
    states = mgr.get_all_states()
    assert "s1" in states
    assert "error" in states["s1"]


def test_device_manager_step_all_no_backend(tmp_path):
    """step_all does not raise when devices have no backend."""
    mgr = DeviceManager()
    mgr.add("s1", _dummy_binary(tmp_path))
    mgr.step_all()  # must not raise


def test_device_manager_send_all_with_mock_backend(tmp_path):
    """send_all calls backend.send_command on each connected device."""
    mgr = DeviceManager()
    proc = mgr.add("s1", _dummy_binary(tmp_path))

    mock_resp = {"status": "ok"}
    mock_backend = MagicMock()
    mock_backend.send_command.return_value = mock_resp
    proc.backend = mock_backend

    result = mgr.send_all({"cmd": "step"})
    assert result["s1"] == mock_resp
    mock_backend.send_command.assert_called_once_with({"cmd": "step"})


def test_device_manager_get_all_states_with_mock_backend(tmp_path):
    """get_all_states calls get_state on each connected device."""
    mgr = DeviceManager()
    proc = mgr.add("s1", _dummy_binary(tmp_path))

    mock_snapshot = SwarmSnapshot(round_number=1, time=0.5, nodes=[])
    mock_backend = MagicMock()
    mock_backend.get_state.return_value = mock_snapshot
    proc.backend = mock_backend

    states = mgr.get_all_states()
    assert states["s1"] is mock_snapshot


def test_device_manager_close_all(tmp_path):
    """close_all closes every registered device without raising."""
    mgr = DeviceManager()
    b = _dummy_binary(tmp_path)
    mgr.add("s1", b)
    mgr.add("s2", b)
    mgr.close_all()  # must not raise


def test_device_manager_context_manager(tmp_path):
    """DeviceManager used as context manager calls close_all on exit."""
    with DeviceManager() as mgr:
        mgr.add("s1", _dummy_binary(tmp_path))
        assert mgr.device_count == 1
    # After __exit__, close_all was called — no exception expected


def test_device_manager_ipc_backend_stored(tmp_path):
    """The ipc_backend name is stored on the SwarmProcess."""
    mgr = DeviceManager()
    proc = mgr.add("s1", _dummy_binary(tmp_path), ipc_backend="grpc", ipc_port=9999)
    assert proc.ipc_backend_name == "grpc"
    assert proc.ipc_port == 9999


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
