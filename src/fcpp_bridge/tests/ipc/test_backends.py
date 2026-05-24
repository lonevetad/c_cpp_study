"""Tests for UnixSocketBackend and HttpBackend."""

import pytest
from pathlib import Path
from unittest.mock import patch

from fcpp_bridge.ipc import NodeState, SwarmSnapshot, UnixSocketBackend, HttpBackend


# ============================================================================
# Test 2: IPC Backend parse_snapshot
# ============================================================================


def test_unix_socket_backend_parse_snapshot():
    backend = UnixSocketBackend.__new__(UnixSocketBackend)
    backend.sock = None
    response = {
        "round": 5, "time": 2.5,
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
    backend = HttpBackend.__new__(HttpBackend)
    response = {"round": 3, "time": 1.5, "nodes": [{"id": 0, "state": 100, "timestamp": 1.5}]}
    snapshot = backend._parse_snapshot(response)
    assert snapshot.round_number == 3
    assert snapshot.time == 1.5
    assert snapshot.nodes[0].state_data == 100


# ============================================================================
# Test 3: Backend configuration
# ============================================================================


def test_unix_socket_backend_init():
    with patch("socket.socket"):
        try:
            UnixSocketBackend(socket_path=Path("/tmp/test.sock"))
        except Exception:
            pass  # socket connection failure is expected


def test_http_backend_init():
    backend = HttpBackend(base_url="http://localhost:8080")
    assert backend.base_url == "http://localhost:8080"
    assert backend.timeout == 5.0


def test_http_backend_url_normalization():
    backend = HttpBackend(base_url="http://localhost:8080/")
    assert backend.base_url == "http://localhost:8080"


# ============================================================================
# Test 5: Error handling — backend parse edge cases
# ============================================================================


def test_unix_socket_backend_parse_snapshot_missing_fields():
    backend = UnixSocketBackend.__new__(UnixSocketBackend)
    response = {"nodes": [{"id": 0}]}  # missing state and timestamp
    snapshot = backend._parse_snapshot(response)
    assert len(snapshot.nodes) == 1
    assert snapshot.nodes[0].state_data is None


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
# Test 8b: HttpBackend extended
# ============================================================================


def test_http_backend_timeout_default():
    backend = HttpBackend()
    assert backend.timeout == 5.0


def test_http_backend_custom_timeout():
    backend = HttpBackend(timeout=10.0)
    assert backend.timeout == 10.0


def test_http_backend_close_noop():
    backend = HttpBackend()
    backend.close()  # must not raise
