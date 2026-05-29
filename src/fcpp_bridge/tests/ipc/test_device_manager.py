"""Tests for DeviceManager — multi-swarm lifecycle coordination."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock

from fcpp_bridge.ipc import DeviceManager, SwarmProcess, PhysicalNode, SwarmSnapshot


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


# ============================================================================
# Physical device support (v1.2)
# ============================================================================


def test_device_manager_add_physical_returns_physical_node():
    mgr = DeviceManager()
    node = mgr.add_physical("robot1", "192.168.1.100", 8080)
    assert isinstance(node, PhysicalNode)
    assert "robot1" in mgr.device_names


def test_device_manager_add_physical_stores_host_port():
    mgr = DeviceManager()
    node = mgr.add_physical("drone1", "10.0.0.5", 50051, backend_type="grpc")
    assert node.host == "10.0.0.5"
    assert node.port == 50051
    assert node.backend_type == "grpc"


def test_device_manager_add_physical_duplicate_raises():
    mgr = DeviceManager()
    mgr.add_physical("r1", "192.168.1.1", 8080)
    with pytest.raises(ValueError, match="r1"):
        mgr.add_physical("r1", "192.168.1.2", 8080)


def test_device_manager_add_simulation_returns_swarm_process(tmp_path):
    mgr = DeviceManager()
    proc = mgr.add_simulation("sim1", _dummy_binary(tmp_path), num_nodes=50)
    assert isinstance(proc, SwarmProcess)
    assert "sim1" in mgr.device_names
    assert proc.num_nodes == 50


def test_device_manager_get_returns_physical_node():
    mgr = DeviceManager()
    node = mgr.add_physical("r1", "192.168.1.1", 8080)
    assert mgr.get("r1") is node


def test_device_manager_step_all_skips_physical_nodes(tmp_path):
    mgr = DeviceManager()

    # Add a SwarmProcess with a mock backend
    sim = mgr.add_simulation("sim", _dummy_binary(tmp_path))
    sim.backend = MagicMock()

    # Add a PhysicalNode — step_all must NOT call step() on it
    node = mgr.add_physical("robot", "localhost", 9000)
    node_step = MagicMock()
    node.step = node_step  # inject a fake step; should never be called

    mgr.step_all()

    sim.backend.send_command.assert_called_once()  # sim was stepped
    node_step.assert_not_called()                   # physical node was skipped


def test_device_manager_total_nodes_mixed(tmp_path):
    mgr = DeviceManager()
    mgr.add_simulation("sim", _dummy_binary(tmp_path), num_nodes=100)
    # A fresh PhysicalNode with no snapshots has node_count == 1
    mgr.add_physical("robot", "localhost", 9000)
    assert mgr.total_nodes() == 101


def test_device_manager_device_count_includes_both_types(tmp_path):
    mgr = DeviceManager()
    mgr.add_simulation("sim", _dummy_binary(tmp_path))
    mgr.add_physical("r1", "192.168.1.1", 8080)
    assert mgr.device_count == 2


# ── Step D — accept_registrations ────────────────────────────────────────────


def _post_register(port: int, payload: dict) -> tuple:
    """POST JSON to /register on localhost:port. Returns (status_code, body_dict)."""
    import urllib.request
    import json
    body = json.dumps(payload).encode()
    req = urllib.request.Request(
        f"http://localhost:{port}/register",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=3) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, {}


def test_accept_registrations_adds_device():
    """Valid POST /register adds the device to the manager."""
    import time
    mgr = DeviceManager()
    mgr.accept_registrations(port=19876)
    time.sleep(0.1)
    try:
        status, body = _post_register(19876, {
            "version": "1.0", "name": "drone-1",
            "host": "127.0.0.1", "port": 8080, "backend": "http",
        })
        assert status == 200
        assert body.get("status") == "ok"
        assert "drone-1" in mgr.device_names
    finally:
        mgr.stop_accepting_registrations()


def test_accept_registrations_invalid_json_returns_400():
    """POST with missing required fields returns 400."""
    import time
    mgr = DeviceManager()
    mgr.accept_registrations(port=19877)
    time.sleep(0.1)
    try:
        status, _ = _post_register(19877, {"incomplete": "payload"})
        assert status == 400
    finally:
        mgr.stop_accepting_registrations()


def test_accept_registrations_wrong_path_returns_404():
    """POST to a path other than /register returns 404."""
    import time, urllib.request, urllib.error
    mgr = DeviceManager()
    mgr.accept_registrations(port=19878)
    time.sleep(0.1)
    try:
        req = urllib.request.Request(
            "http://localhost:19878/other",
            data=b"{}",
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            urllib.request.urlopen(req, timeout=2)
            assert False, "Expected 404"
        except urllib.error.HTTPError as e:
            assert e.code == 404
    finally:
        mgr.stop_accepting_registrations()


def test_accept_registrations_calls_on_registered_callback():
    """on_registered callback fires with (name, node) on valid registration."""
    import time
    registered = []
    mgr = DeviceManager()
    mgr.accept_registrations(port=19879, on_registered=lambda n, node: registered.append(n))
    time.sleep(0.1)
    try:
        _post_register(19879, {
            "version": "1.0", "name": "sensor-1",
            "host": "127.0.0.1", "port": 9090, "backend": "http",
        })
        time.sleep(0.05)
        assert "sensor-1" in registered
    finally:
        mgr.stop_accepting_registrations()


def test_stop_accepting_registrations_clears_thread():
    """After stop, _registration_thread is None."""
    import time
    mgr = DeviceManager()
    mgr.accept_registrations(port=19880)
    time.sleep(0.05)
    mgr.stop_accepting_registrations()
    assert mgr._registration_thread is None
