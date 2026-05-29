import json as _json
import threading
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from ._ipc_node_base import _IpcNodeBase
from .swarm_process import SwarmProcess
from .physical_node import PhysicalNode
from .liveness_strategy import LivenessStrategy
from .output_channel import OutputChannel
from .logging_output_channel import LoggingOutputChannel
from fcpp_bridge.log import get_logger

_log = get_logger(__name__)


class DeviceManager:
    """Manage a heterogeneous fleet of simulation and physical FCPP nodes.

    Supports two kinds of entries:

    * **SwarmProcess** (simulation) — spawns a local C++ binary that simulates
      an entire swarm.  Use :meth:`add_simulation` (or the backward-compatible
      :meth:`add`) to register one.

    * **PhysicalNode** (physical device) — connects to an already-running device
      (robot, drone, phone, sensor …) via HTTP or gRPC.  Use :meth:`add_physical`
      to register one.

    Both types share the same lifecycle API (start/connect, close, listeners,
    heartbeat).  :meth:`step_all` only drives *simulation* nodes; physical nodes
    run their own FCPP round loop.

    Parameters
    ----------
    output_channel:
        Optional :class:`OutputChannel` that receives fleet-wide status events
        (start failures, step failures, close errors).  When omitted a
        :class:`LoggingOutputChannel` at INFO level is used.  Pass a
        :class:`ProxyOutputChannel` to fan-out to multiple destinations.
    """

    def __init__(self, output_channel: Optional[OutputChannel] = None) -> None:
        self._devices: Dict[str, _IpcNodeBase] = {}
        self._output: OutputChannel = output_channel or LoggingOutputChannel()
        self._registration_thread: Optional[threading.Thread] = None
        self._registration_stop_event: Optional[threading.Event] = None
        self._registration_port: Optional[int] = None
        self._registration_callback: Optional[Callable] = None

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def add(
        self,
        name: str,
        binary_path: "Path",
        num_nodes: int = 100,
        ipc_backend: str = "unix",
        ipc_port: Optional[int] = None,
        liveness_strategy: Optional[LivenessStrategy] = None,
    ) -> SwarmProcess:
        """Register a simulation SwarmProcess (backward-compatible alias for add_simulation)."""
        return self.add_simulation(
            name, binary_path, num_nodes, ipc_backend, ipc_port,
            liveness_strategy=liveness_strategy,
        )

    def add_simulation(
        self,
        name: str,
        binary_path: "Path",
        num_nodes: int = 100,
        ipc_backend: str = "unix",
        ipc_port: Optional[int] = None,
        liveness_strategy: Optional[LivenessStrategy] = None,
    ) -> SwarmProcess:
        """Register a simulation swarm that will spawn a local subprocess."""
        if name in self._devices:
            raise ValueError(f"Device '{name}' already registered")
        proc = SwarmProcess(
            binary_path=binary_path,
            num_nodes=num_nodes,
            ipc_backend=ipc_backend,
            ipc_port=ipc_port,
            liveness_strategy=liveness_strategy,
        )
        self._devices[name] = proc
        return proc

    def add_physical(
        self,
        name: str,
        host: str,
        port: int,
        backend_type: str = "http",
        reconnect_interval: float = 5.0,
        liveness_strategy: Optional[LivenessStrategy] = None,
    ) -> PhysicalNode:
        """Register a physical device connection (connects to an existing running device)."""
        if name in self._devices:
            raise ValueError(f"Device '{name}' already registered")
        node = PhysicalNode(
            host=host,
            port=port,
            backend_type=backend_type,
            reconnect_interval=reconnect_interval,
            liveness_strategy=liveness_strategy,
        )
        self._devices[name] = node
        return node

    def remove(self, name: str) -> None:
        """Unregister a device (closes it first if running)."""
        if name not in self._devices:
            raise KeyError(f"No device named '{name}'")
        self._devices[name].close()
        del self._devices[name]

    def get(self, name: str) -> _IpcNodeBase:
        """Return device by name (SwarmProcess or PhysicalNode)."""
        if name not in self._devices:
            raise KeyError(f"No device named '{name}'")
        return self._devices[name]

    @property
    def device_names(self) -> List[str]:
        """List of registered device names."""
        return list(self._devices.keys())

    @property
    def device_count(self) -> int:
        """Number of registered devices."""
        return len(self._devices)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self, name: str) -> None:
        """Start a single named simulation device (SwarmProcess only)."""
        device = self.get(name)
        if not isinstance(device, SwarmProcess):
            raise TypeError(f"'{name}' is a PhysicalNode — call connect() instead of start()")
        device.start()

    def connect(self, name: str) -> None:
        """Connect to a single named physical device (PhysicalNode only)."""
        device = self.get(name)
        if not isinstance(device, PhysicalNode):
            raise TypeError(f"'{name}' is a SwarmProcess — call start() instead of connect()")
        device.connect()

    def start_all(self) -> None:
        """Start all registered simulation devices (skips PhysicalNode entries)."""
        for name, device in self._devices.items():
            if not isinstance(device, SwarmProcess):
                continue
            try:
                device.start()
            except Exception as exc:
                msg = f"Failed to start '{name}': {exc}"
                _log.warning(msg)
                self._output.send("start_all", {"device": name, "error": str(exc)})

    def connect_all(self) -> None:
        """Connect to all registered physical devices (skips SwarmProcess entries)."""
        for name, device in self._devices.items():
            if not isinstance(device, PhysicalNode):
                continue
            try:
                device.connect()
            except Exception as exc:
                msg = f"Failed to connect to '{name}': {exc}"
                _log.warning(msg)
                self._output.send("connect_all", {"device": name, "error": str(exc)})

    def close(self, name: str) -> None:
        """Close a single named device."""
        self.get(name).close()

    def close_all(self) -> None:
        """Close all registered devices."""
        for name, device in list(self._devices.items()):
            try:
                device.close()
            except Exception as exc:
                msg = f"Error closing '{name}': {exc}"
                _log.warning(msg)
                self._output.send("close_all", {"device": name, "error": str(exc)})

    # ------------------------------------------------------------------
    # Fleet-wide operations
    # ------------------------------------------------------------------

    def send_all(self, cmd: Dict[str, Any]) -> Dict[str, Any]:
        """Send the same command to every connected device."""
        results: Dict[str, Any] = {}
        for name, device in self._devices.items():
            if device.backend is None:
                results[name] = {"error": "not connected"}
                continue
            try:
                results[name] = device.backend.send_command(cmd)
            except Exception as exc:
                results[name] = {"error": str(exc)}
        return results

    def step_all(self) -> None:
        """Execute one simulation round on every connected SwarmProcess.

        PhysicalNode entries are silently skipped — physical devices run
        their own FCPP round loop and do not accept a step command.
        """
        for name, device in self._devices.items():
            if not isinstance(device, SwarmProcess):
                continue  # physical devices drive themselves
            if device.backend is None:
                continue
            try:
                device.step()
            except Exception as exc:
                msg = f"step failed for '{name}': {exc}"
                _log.warning(msg)
                self._output.send("step_all", {"device": name, "error": str(exc)})

    def get_all_states(self) -> Dict[str, Any]:
        """Get current state from every connected device."""
        states: Dict[str, Any] = {}
        for name, device in self._devices.items():
            if device.backend is None:
                states[name] = {"error": "not connected"}
                continue
            try:
                states[name] = device.get_state()
            except Exception as exc:
                states[name] = {"error": str(exc)}
        return states

    def total_nodes(self) -> int:
        """Sum of node_count across all registered devices."""
        return sum(device.node_count for device in self._devices.values())

    # ------------------------------------------------------------------
    # Physical-device self-registration
    # ------------------------------------------------------------------

    def accept_registrations(
        self,
        port: int,
        on_registered: Optional[Callable[[str, "PhysicalNode"], None]] = None,
    ) -> None:
        """Start a daemon HTTP server that accepts physical-device self-registrations.

        Devices POST JSON to ``/register``:

        .. code-block:: json

            {"version": "1.0", "name": "drone-7", "host": "192.168.1.50",
             "port": 8080, "backend": "http"}

        On a valid payload, :meth:`add_physical` is called and the optional
        ``on_registered`` callback fires with ``(name, node)``.

        Idempotent — calling again while already running is a no-op.

        Parameters
        ----------
        port:
            TCP port for the registration HTTP server.
        on_registered:
            Optional callback invoked after each successful registration:
            ``on_registered(name, node)``.
        """
        if self._registration_thread is not None and self._registration_thread.is_alive():
            return
        self._registration_port = port
        self._registration_callback = on_registered
        self._registration_stop_event = threading.Event()
        self._registration_thread = threading.Thread(
            target=self._registration_server_loop,
            daemon=True,
            name=f"DeviceManager-registrations-{port}",
        )
        self._registration_thread.start()
        _log.info("Accepting device registrations on port %d", port)

    def stop_accepting_registrations(self) -> None:
        """Stop the device-registration server (waits up to 2 s)."""
        if self._registration_stop_event is not None:
            self._registration_stop_event.set()
        if self._registration_thread is not None:
            self._registration_thread.join(timeout=2.0)
        self._registration_thread = None
        self._registration_stop_event = None
        self._registration_port = None
        self._registration_callback = None

    def _registration_server_loop(self) -> None:
        import http.server

        manager = self

        class _Handler(http.server.BaseHTTPRequestHandler):
            def do_POST(self_h):
                if self_h.path != "/register":
                    self_h.send_response(404)
                    self_h.end_headers()
                    return
                length = int(self_h.headers.get("Content-Length", 0))
                body = self_h.rfile.read(length)
                try:
                    data = _json.loads(body)
                    name = data["name"]
                    host = data["host"]
                    port = int(data["port"])
                    backend = data.get("backend", "http")
                    node = manager.add_physical(name, host, port, backend_type=backend)
                    if manager._registration_callback:
                        manager._registration_callback(name, node)
                    self_h.send_response(200)
                    self_h.end_headers()
                    self_h.wfile.write(b'{"status":"ok"}')
                except Exception as exc:
                    self_h.send_response(400)
                    self_h.end_headers()
                    self_h.wfile.write(_json.dumps({"error": str(exc)}).encode())

            def log_message(self_h, *args):
                pass  # suppress BaseHTTPServer stderr output

        server = http.server.HTTPServer(("", manager._registration_port), _Handler)
        server.timeout = 0.5  # poll for stop_event
        assert manager._registration_stop_event is not None
        while not manager._registration_stop_event.is_set():
            server.handle_request()
        server.server_close()

    # ------------------------------------------------------------------
    # Context manager
    # ------------------------------------------------------------------

    def __enter__(self) -> "DeviceManager":
        return self

    def __exit__(self, *args) -> None:
        self.stop_accepting_registrations()
        self.close_all()
