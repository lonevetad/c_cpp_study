"""Tests for the pluggable liveness strategy system."""

import time
import pytest
from unittest.mock import MagicMock
from pathlib import Path

from fcpp_bridge.ipc import (
    SwarmProcess,
    PhysicalNode,
    SwarmSnapshot,
    NodeState,
    PassiveHeartbeatStrategy,
    ActivePingStrategy,
    AlwaysAliveStrategy,
    LivenessStrategy,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _snap(*node_ids: int) -> SwarmSnapshot:
    nodes = [NodeState(node_id=nid, state_data={}, timestamp=0.0) for nid in node_ids]
    return SwarmSnapshot(round_number=0, time=0.0, nodes=nodes)


# ===========================================================================
# PassiveHeartbeatStrategy
# ===========================================================================


def test_passive_default_timeout():
    s = PassiveHeartbeatStrategy()
    assert s.timeout == 30.0


def test_passive_custom_timeout():
    s = PassiveHeartbeatStrategy(timeout=10.0)
    assert s.timeout == 10.0


def test_passive_on_snapshot_records_nodes():
    s = PassiveHeartbeatStrategy()
    before = time.time()
    s.on_snapshot(_snap(1, 2, 3))
    for nid in (1, 2, 3):
        assert nid in s._timestamps
        assert s._timestamps[nid] >= before


def test_passive_check_alive_within_timeout():
    s = PassiveHeartbeatStrategy(timeout=30.0)
    s.on_snapshot(_snap(5))
    result = s.check()
    assert result[5] is True


def test_passive_check_dead_outside_timeout():
    s = PassiveHeartbeatStrategy(timeout=5.0)
    s._timestamps[7] = time.time() - 10.0  # 10 s ago
    result = s.check()
    assert result[7] is False


def test_passive_check_timeout_override():
    s = PassiveHeartbeatStrategy(timeout=5.0)
    s._timestamps[9] = time.time() - 8.0  # dead with default, alive with 30
    assert s.check(timeout=30.0)[9] is True
    assert s.check(timeout=5.0)[9] is False


def test_passive_discard_removes_node():
    s = PassiveHeartbeatStrategy()
    s._timestamps[3] = time.time()
    s.discard(3)
    assert 3 not in s._timestamps
    assert 3 not in s.check()


def test_passive_check_ignores_unknown_kwargs():
    s = PassiveHeartbeatStrategy()
    s.on_snapshot(_snap(1))
    # Should not raise
    result = s.check(timeout=5.0, unknown_param="ignored")
    assert 1 in result


# ===========================================================================
# ActivePingStrategy
# ===========================================================================


def test_active_on_snapshot_records_ids():
    mock_backend = MagicMock()
    s = ActivePingStrategy(backend_getter=lambda: mock_backend)
    s.on_snapshot(_snap(10, 20))
    assert 10 in s._known_ids
    assert 20 in s._known_ids


def test_active_check_returns_true_on_pong():
    mock_backend = MagicMock()
    mock_backend.send_command.return_value = {"status": "pong"}
    s = ActivePingStrategy(backend_getter=lambda: mock_backend)
    s.on_snapshot(_snap(1))
    result = s.check()
    assert result[1] is True
    mock_backend.send_command.assert_called_once_with(
        {"cmd": "ping", "node_id": 1, "timeout": 2.0}
    )


def test_active_check_returns_false_on_wrong_response():
    mock_backend = MagicMock()
    mock_backend.send_command.return_value = {"status": "error"}
    s = ActivePingStrategy(backend_getter=lambda: mock_backend)
    s.on_snapshot(_snap(2))
    result = s.check()
    assert result[2] is False


def test_active_check_returns_false_on_exception():
    mock_backend = MagicMock()
    mock_backend.send_command.side_effect = ConnectionError("lost")
    s = ActivePingStrategy(backend_getter=lambda: mock_backend)
    s.on_snapshot(_snap(3))
    result = s.check()
    assert result[3] is False


def test_active_check_no_backend_returns_all_false():
    s = ActivePingStrategy(backend_getter=lambda: None)
    s.on_snapshot(_snap(1, 2))
    result = s.check()
    assert result == {1: False, 2: False}


def test_active_check_ping_timeout_override():
    mock_backend = MagicMock()
    mock_backend.send_command.return_value = {"status": "pong"}
    s = ActivePingStrategy(backend_getter=lambda: mock_backend, ping_timeout=2.0)
    s.on_snapshot(_snap(5))
    s.check(ping_timeout=0.5)
    mock_backend.send_command.assert_called_once_with(
        {"cmd": "ping", "node_id": 5, "timeout": 0.5}
    )


def test_active_discard_removes_node():
    mock_backend = MagicMock()
    mock_backend.send_command.return_value = {"status": "pong"}
    s = ActivePingStrategy(backend_getter=lambda: mock_backend)
    s.on_snapshot(_snap(7))
    s.discard(7)
    result = s.check()
    assert 7 not in result


# ===========================================================================
# AlwaysAliveStrategy
# ===========================================================================


def test_always_alive_returns_true_for_all():
    s = AlwaysAliveStrategy()
    s.on_snapshot(_snap(1, 2, 3))
    result = s.check()
    assert result == {1: True, 2: True, 3: True}


def test_always_alive_discard_removes_node():
    s = AlwaysAliveStrategy()
    s.on_snapshot(_snap(1, 2))
    s.discard(1)
    result = s.check()
    assert 1 not in result
    assert result[2] is True


def test_always_alive_ignores_kwargs():
    s = AlwaysAliveStrategy()
    s.on_snapshot(_snap(5))
    result = s.check(timeout=1.0, ping_timeout=0.1)
    assert result[5] is True


# ===========================================================================
# _IpcNodeBase integration — set_liveness_strategy
# ===========================================================================


def test_set_liveness_strategy_replaces_strategy():
    swarm = SwarmProcess(binary_path=Path("/tmp/mock"))
    swarm.backend = MagicMock()
    assert isinstance(swarm._liveness_strategy, PassiveHeartbeatStrategy)

    new_strat = AlwaysAliveStrategy()
    swarm.set_liveness_strategy(new_strat)
    assert swarm._liveness_strategy is new_strat


def test_set_liveness_strategy_closes_old():
    swarm = SwarmProcess(binary_path=Path("/tmp/mock"))
    old_strat = MagicMock(spec=LivenessStrategy)
    swarm._liveness_strategy = old_strat

    swarm.set_liveness_strategy(AlwaysAliveStrategy())
    old_strat.close.assert_called_once()


def test_liveness_strategy_constructor_kwarg():
    strat = AlwaysAliveStrategy()
    swarm = SwarmProcess(binary_path=Path("/tmp/mock"), liveness_strategy=strat)
    assert swarm._liveness_strategy is strat


def test_liveness_strategy_constructor_kwarg_physical():
    strat = AlwaysAliveStrategy()
    node = PhysicalNode("localhost", 9000, liveness_strategy=strat)
    assert node._liveness_strategy is strat


def test_check_liveness_uses_active_strategy():
    mock_backend = MagicMock()
    mock_backend.send_command.return_value = {"status": "pong"}
    swarm = SwarmProcess(
        binary_path=Path("/tmp/mock"),
        liveness_strategy=ActivePingStrategy(lambda: mock_backend),
    )
    swarm.backend = mock_backend
    swarm._liveness_strategy.on_snapshot(_snap(42))
    result = swarm.check_liveness()
    assert result[42] is True


# ── Step D — Ping handler + pong round-trip ───────────────────────────────────


def test_active_ping_bad_response_returns_false():
    """Backend returns a non-pong response → node is reported dead."""
    mock_backend = MagicMock()
    mock_backend.send_command.return_value = {"status": "error"}
    strat = ActivePingStrategy(lambda: mock_backend)
    strat.on_snapshot(_snap(7))
    result = strat.check()
    assert result[7] is False


def test_ping_handler_present_in_cpp_template():
    """main_template_header() must contain the standard ping/pong handler."""
    from fcpp_bridge.runtime.runtime_generator import RuntimeGenerator
    template = RuntimeGenerator.main_template_header()
    assert '"ping"' in template
    assert '"pong"' in template
    assert "register_handler" in template


def test_active_ping_docstring_no_longer_requires_binary():
    """ActivePingStrategy docstring must not say 'Requires' the C++ binary handler."""
    doc = ActivePingStrategy.__doc__ or ""
    assert "registered automatically" in doc
    assert "Requires" not in doc
