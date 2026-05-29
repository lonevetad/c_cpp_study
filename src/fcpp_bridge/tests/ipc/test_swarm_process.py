"""Tests for SwarmProcess — subprocess lifecycle and IPC integration."""

import os
import tempfile
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from fcpp_bridge.ipc import SwarmProcess, SwarmSnapshot


# ============================================================================
# Test 4: Swarm Process Management
# ============================================================================


def test_swarm_process_init():
    swarm = SwarmProcess(
        binary_path=Path("/tmp/mock_swarm"),
        num_nodes=100,
        ipc_backend="unix",
    )
    assert swarm.binary_path == Path("/tmp/mock_swarm")
    assert swarm.num_nodes == 100
    assert swarm.ipc_backend_name == "unix"


def test_swarm_process_context_manager():
    mock_proc = MagicMock()
    mock_backend = MagicMock()
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
    swarm = SwarmProcess(binary_path=Path("/tmp/mock"), num_nodes=10)
    swarm.backend = MagicMock()
    swarm.add_nodes(5)
    assert swarm.num_nodes == 15
    swarm.backend.send_command.assert_called_once()


# ============================================================================
# Test 5: Error Handling
# ============================================================================


def test_swarm_process_missing_binary():
    swarm = SwarmProcess(binary_path=Path("/nonexistent/path"))
    with pytest.raises(FileNotFoundError):
        swarm.start()


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
    swarm = SwarmProcess(binary_path=Path("/tmp/mock"), ipc_backend="http://localhost:9090")
    assert swarm.ipc_backend_name == "http://localhost:9090"


def test_swarm_process_ipc_backend_grpc():
    swarm = SwarmProcess(binary_path=Path("/tmp/mock"), ipc_backend="grpc")
    assert swarm.ipc_backend_name == "grpc"


def test_swarm_process_step_calls_backend():
    swarm = SwarmProcess(binary_path=Path("/tmp/mock"))
    swarm.backend = MagicMock()
    swarm.step()
    swarm.backend.send_command.assert_called_once_with({"cmd": "step"})


def test_swarm_process_get_state_calls_backend():
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
