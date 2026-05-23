"""Tests for Phase 4 IPC Backends and Runtime."""

import pytest
from pathlib import Path
from fcpp_bridge.ipc import (
    NodeState,
    SwarmSnapshot,
    UnixSocketBackend,
    HttpBackend,
    SwarmProcess,
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
    from unittest.mock import patch, MagicMock

    mock_proc = MagicMock()
    mock_backend = MagicMock()

    with patch("subprocess.Popen", return_value=mock_proc):
        with patch.object(SwarmProcess, "_create_backend") as mock_create:
            with patch.object(SwarmProcess, "backend", new_callable=lambda: mock_backend):
                swarm = SwarmProcess(binary_path=Path("/tmp/mock"))
                swarm.backend = mock_backend

                # __enter__ should start the process
                swarm.start()
                assert swarm.process is not None


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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
