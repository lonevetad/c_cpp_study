"""Tests for OutputChannel hierarchy — Step C."""

import io
import json
import pytest
from unittest.mock import MagicMock

from fcpp_bridge.ipc import (
    OutputChannel,
    LoggingOutputChannel,
    FileOutputChannel,
    CallbackOutputChannel,
    ProxyOutputChannel,
)


# ============================================================================
# 1. LoggingOutputChannel
# ============================================================================

def test_logging_output_channel_send_calls_logger(caplog):
    ch = LoggingOutputChannel(level="INFO")
    import logging
    with caplog.at_level(logging.INFO, logger="fcpp_bridge.output"):
        ch.send("test_event", {"key": "val"})
    assert "test_event" in caplog.text


def test_logging_output_channel_clone_shares_logger():
    ch = LoggingOutputChannel(level="WARNING")
    clone = ch.clone()
    assert clone._logger is ch._logger
    assert clone._level == "WARNING"


# ============================================================================
# 2. CallbackOutputChannel
# ============================================================================

def test_callback_output_channel_invokes_fn():
    calls = []
    ch = CallbackOutputChannel(lambda name, payload: calls.append((name, payload)))
    ch.send("evt", 42)
    assert calls == [("evt", 42)]


def test_callback_output_channel_clone_uses_same_fn():
    fn = MagicMock()
    ch = CallbackOutputChannel(fn)
    clone = ch.clone()
    clone.send("x", "y")
    fn.assert_called_once_with("x", "y")


def test_callback_output_channel_close_is_noop():
    ch = CallbackOutputChannel(lambda n, p: None)
    ch.close()  # must not raise


# ============================================================================
# 3. FileOutputChannel
# ============================================================================

def test_file_output_channel_json_format():
    buf = io.StringIO()
    ch = FileOutputChannel(buf, format="json")
    ch.send("event", {"a": 1})
    buf.seek(0)
    row = json.loads(buf.read())
    assert row["name"] == "event"
    assert row["payload"] == {"a": 1}


def test_file_output_channel_csv_format():
    buf = io.StringIO()
    ch = FileOutputChannel(buf, format="csv")
    ch.send("step", "ok")
    buf.seek(0)
    line = buf.read()
    assert "step" in line
    assert "ok" in line


def test_file_output_channel_clone_does_not_own_stream():
    buf = io.StringIO()
    ch = FileOutputChannel(buf, format="json")
    clone = ch.clone()
    assert not clone._owns_stream
    clone.close()  # must not close the shared stream
    ch.send("after", "clone_close")  # stream still usable
    buf.seek(0)
    assert "after" in buf.read()


# ============================================================================
# 4. ProxyOutputChannel
# ============================================================================

def test_proxy_sends_to_all_sequential():
    calls = []
    proxy = ProxyOutputChannel(mode="sequential")
    proxy.add_channel(CallbackOutputChannel(lambda n, p: calls.append(("A", n, p))))
    proxy.add_channel(CallbackOutputChannel(lambda n, p: calls.append(("B", n, p))))
    proxy.send("evt", 1)
    assert ("A", "evt", 1) in calls
    assert ("B", "evt", 1) in calls


def test_proxy_sends_to_all_parallel():
    calls = []
    proxy = ProxyOutputChannel(mode="parallel")
    proxy.add_channel(CallbackOutputChannel(lambda n, p: calls.append(("A", n, p))))
    proxy.add_channel(CallbackOutputChannel(lambda n, p: calls.append(("B", n, p))))
    proxy.send("evt", 2)
    assert len(calls) == 2


def test_proxy_remove_channel():
    calls = []
    proxy = ProxyOutputChannel()
    cid = proxy.add_channel(CallbackOutputChannel(lambda n, p: calls.append(p)))
    proxy.remove_channel(cid)
    proxy.send("x", 99)
    assert calls == []


def test_proxy_invalid_mode_raises():
    with pytest.raises(ValueError):
        ProxyOutputChannel(mode="fire_and_forget")


def test_proxy_clone_copies_channels():
    calls_orig, calls_clone = [], []
    proxy = ProxyOutputChannel()
    proxy.add_channel(CallbackOutputChannel(lambda n, p: calls_orig.append(p)))
    clone = proxy.clone()
    # Replace the clone's channel with a different one to verify independence
    clone._channels.clear()
    clone.add_channel(CallbackOutputChannel(lambda n, p: calls_clone.append(p)))
    proxy.send("orig", 1)
    clone.send("clone", 2)
    assert calls_orig == [1]
    assert calls_clone == [2]


# ============================================================================
# 5. DeviceManager output_channel integration
# ============================================================================

def test_device_manager_accepts_output_channel():
    from fcpp_bridge.ipc import DeviceManager
    calls = []
    dm = DeviceManager(output_channel=CallbackOutputChannel(
        lambda n, p: calls.append(n)
    ))
    assert dm._output is not None


def test_device_manager_start_all_failure_reaches_output_channel():
    from fcpp_bridge.ipc import DeviceManager
    from unittest.mock import create_autospec
    from fcpp_bridge.ipc.swarm_process import SwarmProcess
    calls = []
    dm = DeviceManager(output_channel=CallbackOutputChannel(
        lambda n, p: calls.append((n, p))
    ))
    mock_proc = create_autospec(SwarmProcess, instance=True)
    mock_proc.start.side_effect = RuntimeError("binary missing")
    dm._devices["sim1"] = mock_proc
    dm.start_all()
    assert any(n == "start_all" for n, p in calls)
    assert any(p.get("device") == "sim1" for n, p in calls)
