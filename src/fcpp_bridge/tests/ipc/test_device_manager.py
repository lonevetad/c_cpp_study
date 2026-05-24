"""Tests for DeviceManager — multi-swarm lifecycle coordination."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock

from fcpp_bridge.ipc import DeviceManager, SwarmProcess, SwarmSnapshot


def _dummy_binary(tmp_path):
    p = tmp_path / "dummy_bin"
    p.write_bytes(b"")
    p.chmod(0o755)
    return p


def test_device_manager_instantiation():
    mgr = DeviceManager()
    assert mgr.device_count == 0
    assert mgr.device_names == []


def test_device_manager_add(tmp_path):
    mgr = DeviceManager()
    proc = mgr.add("s1", _dummy_binary(tmp_path))
    assert "s1" in mgr.device_names
    assert mgr.device_count == 1
    assert isinstance(proc, SwarmProcess)


def test_device_manager_add_duplicate_raises(tmp_path):
    mgr = DeviceManager()
    b = _dummy_binary(tmp_path)
    mgr.add("s1", b)
    with pytest.raises(ValueError, match="s1"):
        mgr.add("s1", b)


def test_device_manager_get(tmp_path):
    mgr = DeviceManager()
    proc = mgr.add("s1", _dummy_binary(tmp_path))
    assert mgr.get("s1") is proc


def test_device_manager_get_missing_raises():
    mgr = DeviceManager()
    with pytest.raises(KeyError):
        mgr.get("no_such_device")


def test_device_manager_remove(tmp_path):
    mgr = DeviceManager()
    mgr.add("s1", _dummy_binary(tmp_path))
    mgr.remove("s1")
    assert mgr.device_count == 0


def test_device_manager_remove_missing_raises():
    mgr = DeviceManager()
    with pytest.raises(KeyError):
        mgr.remove("ghost")


def test_device_manager_device_names_order(tmp_path):
    mgr = DeviceManager()
    b = _dummy_binary(tmp_path)
    mgr.add("alpha", b)
    mgr.add("beta", b)
    mgr.add("gamma", b)
    assert mgr.device_names == ["alpha", "beta", "gamma"]


def test_device_manager_total_nodes(tmp_path):
    mgr = DeviceManager()
    b = _dummy_binary(tmp_path)
    mgr.add("s1", b, num_nodes=50)
    mgr.add("s2", b, num_nodes=150)
    assert mgr.total_nodes() == 200


def test_device_manager_send_all_no_backend(tmp_path):
    mgr = DeviceManager()
    mgr.add("s1", _dummy_binary(tmp_path))
    result = mgr.send_all({"cmd": "step"})
    assert "s1" in result
    assert "error" in result["s1"]


def test_device_manager_get_all_states_no_backend(tmp_path):
    mgr = DeviceManager()
    mgr.add("s1", _dummy_binary(tmp_path))
    states = mgr.get_all_states()
    assert "s1" in states
    assert "error" in states["s1"]


def test_device_manager_step_all_no_backend(tmp_path):
    mgr = DeviceManager()
    mgr.add("s1", _dummy_binary(tmp_path))
    mgr.step_all()  # must not raise


def test_device_manager_send_all_with_mock_backend(tmp_path):
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
    mgr = DeviceManager()
    proc = mgr.add("s1", _dummy_binary(tmp_path))
    mock_snapshot = SwarmSnapshot(round_number=1, time=0.5, nodes=[])
    mock_backend = MagicMock()
    mock_backend.get_state.return_value = mock_snapshot
    proc.backend = mock_backend
    states = mgr.get_all_states()
    assert states["s1"] is mock_snapshot


def test_device_manager_close_all(tmp_path):
    mgr = DeviceManager()
    b = _dummy_binary(tmp_path)
    mgr.add("s1", b)
    mgr.add("s2", b)
    mgr.close_all()  # must not raise


def test_device_manager_context_manager(tmp_path):
    with DeviceManager() as mgr:
        mgr.add("s1", _dummy_binary(tmp_path))
        assert mgr.device_count == 1


def test_device_manager_ipc_backend_stored(tmp_path):
    mgr = DeviceManager()
    proc = mgr.add("s1", _dummy_binary(tmp_path), ipc_backend="grpc", ipc_port=9999)
    assert proc.ipc_backend_name == "grpc"
    assert proc.ipc_port == 9999
