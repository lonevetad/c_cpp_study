"""IPC backends — communicate with running swarms."""

import subprocess
import json
import socket
import threading
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, Optional, Callable, List
from dataclasses import dataclass, asdict


@dataclass
class NodeState:
    """State of a single node in the swarm."""

    node_id: int
    state_data: Any
    timestamp: float


@dataclass
class SwarmSnapshot:
    """Snapshot of entire swarm state at a point in time."""

    round_number: int
    time: float
    nodes: List[NodeState]


class IpcBackend(ABC):
    """Abstract base for communication with compiled swarms."""

    @abstractmethod
    def send_command(self, cmd: Dict[str, Any]) -> Dict[str, Any]:
        """Send command to swarm; receive response."""
        pass

    @abstractmethod
    def get_state(self) -> SwarmSnapshot:
        """Get current swarm state."""
        pass

    def subscribe_state_updates(
        self, callback: Callable[[SwarmSnapshot], None]
    ) -> None:
        """Subscribe to continuous state updates (optional; default: noop).

        Backends that support streaming (gRPC) override this; polling
        backends (Unix socket, HTTP) leave the default no-op in place.
        """

    @abstractmethod
    def close(self) -> None:
        """Close connection."""
        pass


class UnixSocketBackend(IpcBackend):
    """
    Unix socket backend (default).

    Swarm listens on /tmp/fcpp_swarm_<pid>.sock
    """

    def __init__(self, socket_path: Optional[Path] = None, timeout: float = 5.0):
        self.socket_path = socket_path or Path(f"/tmp/fcpp_swarm.sock")
        self.timeout = timeout
        self.sock: Optional[socket.socket] = None
        self._connect()

    def _connect(self) -> None:
        """Connect to swarm socket."""
        try:
            self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self.sock.settimeout(self.timeout)
            self.sock.connect(str(self.socket_path))
        except (FileNotFoundError, ConnectionRefusedError) as e:
            raise RuntimeError(f"Cannot connect to swarm at {self.socket_path}: {e}")

    def send_command(self, cmd: Dict[str, Any]) -> Dict[str, Any]:
        """Send JSON command and receive JSON response."""
        if not self.sock:
            raise RuntimeError("Not connected")

        # Serialize command to JSON
        request = json.dumps(cmd).encode() + b"\n"

        try:
            self.sock.sendall(request)

            # Receive response
            response_data = b""
            while b"\n" not in response_data:
                chunk = self.sock.recv(4096)
                if not chunk:
                    raise RuntimeError("Connection closed by swarm")
                response_data += chunk

            return json.loads(response_data.decode())
        except socket.timeout:
            raise RuntimeError(f"IPC timeout after {self.timeout}s")

    def get_state(self) -> SwarmSnapshot:
        """Get current swarm state."""
        response = self.send_command({"cmd": "get_state"})
        return self._parse_snapshot(response)

    def _parse_snapshot(self, response: Dict[str, Any]) -> SwarmSnapshot:
        """Convert IPC response to SwarmSnapshot."""
        nodes = [
            NodeState(
                node_id=n["id"],
                state_data=n.get("state"),
                timestamp=n.get("timestamp", 0.0),
            )
            for n in response.get("nodes", [])
        ]
        return SwarmSnapshot(
            round_number=response.get("round", 0),
            time=response.get("time", 0.0),
            nodes=nodes,
        )

    def close(self) -> None:
        """Close socket connection."""
        if self.sock:
            self.sock.close()
            self.sock = None


class HttpBackend(IpcBackend):
    """
    HTTP/REST backend.

    Swarm listens on http://localhost:PORT
    """

    def __init__(self, base_url: str = "http://localhost:8080", timeout: float = 5.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def send_command(self, cmd: Dict[str, Any]) -> Dict[str, Any]:
        """Send POST request with command."""
        try:
            import requests

            url = f"{self.base_url}/command"
            response = requests.post(
                url,
                json=cmd,
                timeout=self.timeout,
            )
            response.raise_for_status()
            return response.json()
        except ImportError:
            raise RuntimeError("requests library not installed; install with: pip install requests")
        except Exception as e:
            raise RuntimeError(f"HTTP request failed: {e}")

    def get_state(self) -> SwarmSnapshot:
        """GET current swarm state."""
        try:
            import requests

            url = f"{self.base_url}/state"
            response = requests.get(url, timeout=self.timeout)
            response.raise_for_status()
            return self._parse_snapshot(response.json())
        except ImportError:
            raise RuntimeError("requests library not installed; install with: pip install requests")
        except Exception as e:
            raise RuntimeError(f"HTTP request failed: {e}")

    def _parse_snapshot(self, response: Dict[str, Any]) -> SwarmSnapshot:
        """Convert HTTP response to SwarmSnapshot."""
        nodes = [
            NodeState(
                node_id=n["id"],
                state_data=n.get("state"),
                timestamp=n.get("timestamp", 0.0),
            )
            for n in response.get("nodes", [])
        ]
        return SwarmSnapshot(
            round_number=response.get("round", 0),
            time=response.get("time", 0.0),
            nodes=nodes,
        )

    def close(self) -> None:
        """No resources to clean up for HTTP."""
        pass


class GrpcBackend(IpcBackend):
    """gRPC backend for streaming state updates.

    Requires:
        pip install grpcio grpcio-tools

    Generate Python stubs from fcpp_swarm.proto:
        python -m grpc_tools.protoc \\
            -I src/fcpp_bridge/ipc \\
            --python_out=src/fcpp_bridge/ipc \\
            --grpc_python_out=src/fcpp_bridge/ipc \\
            src/fcpp_bridge/ipc/fcpp_swarm.proto

    The generated modules (fcpp_swarm_pb2.py, fcpp_swarm_pb2_grpc.py) must
    be present in this package before the backend is usable.
    """

    def __init__(self, host: str = "localhost", port: int = 50051, timeout: float = 5.0):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.channel = None
        self.stub = None
        self._stream_thread: Optional[threading.Thread] = None
        self._stream_running = False
        self._connect()

    def _connect(self) -> None:
        """Open gRPC channel and create service stub."""
        try:
            import grpc

            self.channel = grpc.insecure_channel(f"{self.host}:{self.port}")

            # Import generated stubs — must run grpc_tools.protoc first
            try:
                from fcpp_bridge.ipc import (  # type: ignore[attr-defined]
                    fcpp_swarm_pb2_grpc as _grpc_stub,
                )
                self.stub = _grpc_stub.SwarmServiceStub(self.channel)
            except ImportError:
                self.stub = None  # stubs not generated yet; send_command will fail informatively

        except ImportError:
            raise RuntimeError(
                "grpcio not installed. Install with: pip install grpcio grpcio-tools"
            )

    def _require_stub(self) -> None:
        if self.stub is None:
            raise RuntimeError(
                "gRPC stubs not generated. Run:\n"
                "  python -m grpc_tools.protoc "
                "-I src/fcpp_bridge/ipc "
                "--python_out=src/fcpp_bridge/ipc "
                "--grpc_python_out=src/fcpp_bridge/ipc "
                "src/fcpp_bridge/ipc/fcpp_swarm.proto"
            )

    def send_command(self, cmd: Dict[str, Any]) -> Dict[str, Any]:
        """Send a control command to the swarm via gRPC."""
        self._require_stub()

        try:
            from fcpp_bridge.ipc import fcpp_swarm_pb2 as _pb2  # type: ignore[attr-defined]

            request = _pb2.CommandRequest(
                cmd=cmd.get("cmd", ""),
                count=cmd.get("count", 0),
                data=json.dumps(cmd).encode() if cmd else b"",
            )
            response = self.stub.SendCommand(request, timeout=self.timeout)
            result = {"success": response.success, "message": response.message}
            if response.data:
                result.update(json.loads(response.data))
            return result
        except Exception as e:
            raise RuntimeError(f"gRPC send_command failed: {e}") from e

    def get_state(self) -> SwarmSnapshot:
        """Retrieve the current swarm state via gRPC unary call."""
        self._require_stub()

        try:
            from fcpp_bridge.ipc import fcpp_swarm_pb2 as _pb2  # type: ignore[attr-defined]

            request = _pb2.StateRequest(from_round=0)
            response = self.stub.GetState(request, timeout=self.timeout)
            return self._proto_to_snapshot(response)
        except Exception as e:
            raise RuntimeError(f"gRPC get_state failed: {e}") from e

    def subscribe_state_updates(
        self, callback: Callable[[SwarmSnapshot], None]
    ) -> None:
        """Start a background thread that streams state updates via gRPC."""
        self._require_stub()

        def _stream() -> None:
            try:
                from fcpp_bridge.ipc import fcpp_swarm_pb2 as _pb2  # type: ignore[attr-defined]

                request = _pb2.StateRequest(from_round=0)
                for response in self.stub.StreamState(request):
                    if not self._stream_running:
                        break
                    callback(self._proto_to_snapshot(response))
            except Exception:
                pass  # stream closed or server stopped

        self._stream_running = True
        self._stream_thread = threading.Thread(target=_stream, daemon=True)
        self._stream_thread.start()

    def _proto_to_snapshot(self, response: Any) -> SwarmSnapshot:
        """Convert a SwarmStateResponse protobuf message to a SwarmSnapshot."""
        nodes = []
        for n in response.nodes:
            try:
                state_data = json.loads(n.state_json) if n.state_json else None
            except (json.JSONDecodeError, ValueError):
                state_data = n.state_json
            nodes.append(NodeState(
                node_id=n.id,
                state_data=state_data,
                timestamp=n.timestamp,
            ))
        return SwarmSnapshot(
            round_number=response.round_number,
            time=response.sim_time,
            nodes=nodes,
        )

    def close(self) -> None:
        """Stop streaming thread and close gRPC channel."""
        self._stream_running = False
        if self._stream_thread and self._stream_thread.is_alive():
            self._stream_thread.join(timeout=2.0)
        if self.channel:
            self.channel.close()
            self.channel = None


class SwarmProcess:
    """
    Manages a compiled swarm subprocess with IPC communication.

    Usage:
        swarm = SwarmProcess(binary_path, ipc_backend="unix")
        swarm.step()
        state = swarm.get_state()
        swarm.close()
    """

    backend: Optional[IpcBackend] = None  # class-level attr required for patch.object

    def __init__(
        self,
        binary_path: Path,
        num_nodes: int = 100,
        ipc_backend: str = "unix",
        ipc_port: Optional[int] = None,
    ):
        self.binary_path = Path(binary_path)
        self.num_nodes = num_nodes
        self.ipc_backend_name = ipc_backend
        self.ipc_port = ipc_port or 50051
        self.process: Optional[subprocess.Popen] = None
        self.backend: Optional[IpcBackend] = None

    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, *args):
        """Context manager exit."""
        self.close()

    def start(self) -> None:
        """Start the swarm subprocess."""
        if not self.binary_path.exists():
            raise FileNotFoundError(f"Binary not found: {self.binary_path}")

        print(f"[SwarmProcess] Starting {self.binary_path}")

        # Spawn subprocess
        try:
            self.process = subprocess.Popen(
                [str(self.binary_path), f"--num-nodes={self.num_nodes}"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
        except Exception as e:
            raise RuntimeError(f"Failed to start swarm process: {e}")

        # Give subprocess time to start IPC server
        import time
        time.sleep(0.5)

        # Connect IPC backend
        self._create_backend()

    def _create_backend(self) -> None:
        """Create IPC backend based on configuration."""
        if self.ipc_backend_name == "unix":
            self.backend = UnixSocketBackend()
        elif self.ipc_backend_name.startswith("http://"):
            self.backend = HttpBackend(self.ipc_backend_name)
        elif self.ipc_backend_name == "grpc":
            self.backend = GrpcBackend(port=self.ipc_port)
        else:
            raise ValueError(f"Unknown IPC backend: {self.ipc_backend_name}")

        print(f"[SwarmProcess] Connected via {self.ipc_backend_name}")

    def step(self) -> None:
        """Execute one simulation round."""
        if not self.backend:
            raise RuntimeError("Not connected")
        self.backend.send_command({"cmd": "step"})

    def get_state(self) -> SwarmSnapshot:
        """Get current swarm state."""
        if not self.backend:
            raise RuntimeError("Not connected")
        return self.backend.get_state()

    def add_nodes(self, count: int) -> None:
        """Add nodes to running swarm."""
        if not self.backend:
            raise RuntimeError("Not connected")
        self.backend.send_command({"cmd": "add_nodes", "count": count})
        self.num_nodes += count

    def close(self) -> None:
        """Stop swarm and cleanup."""
        if self.backend:
            self.backend.close()
            self.backend = None

        if self.process:
            self.process.terminate()
            try:
                self.process.wait(timeout=5.0)
            except subprocess.TimeoutExpired:
                self.process.kill()
            self.process = None

        print("[SwarmProcess] Closed")


class DeviceManager:
    """
    Manage multiple SwarmProcess instances as named devices.

    Usage::

        mgr = DeviceManager()
        mgr.add("swarm_a", binary_path, num_nodes=50)
        mgr.add("swarm_b", binary_path, num_nodes=100, ipc_backend="grpc")
        mgr.start_all()
        states = mgr.get_all_states()
        mgr.send_all({"cmd": "step"})
        mgr.close_all()

    Also usable as a context manager::

        with DeviceManager() as mgr:
            mgr.add("s1", path)
            mgr.start_all()
    """

    def __init__(self):
        self._devices: Dict[str, SwarmProcess] = {}

    # ------------------------------------------------------------------ #
    # Registration                                                         #
    # ------------------------------------------------------------------ #

    def add(
        self,
        name: str,
        binary_path: "Path",
        num_nodes: int = 100,
        ipc_backend: str = "unix",
        ipc_port: Optional[int] = None,
    ) -> "SwarmProcess":
        """Register a new device (does not start it yet)."""
        if name in self._devices:
            raise ValueError(f"Device '{name}' already registered")
        proc = SwarmProcess(
            binary_path=binary_path,
            num_nodes=num_nodes,
            ipc_backend=ipc_backend,
            ipc_port=ipc_port,
        )
        self._devices[name] = proc
        return proc

    def remove(self, name: str) -> None:
        """Unregister a device (closes it first if running)."""
        if name not in self._devices:
            raise KeyError(f"No device named '{name}'")
        self._devices[name].close()
        del self._devices[name]

    def get(self, name: str) -> "SwarmProcess":
        """Return device by name."""
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

    # ------------------------------------------------------------------ #
    # Lifecycle                                                            #
    # ------------------------------------------------------------------ #

    def start(self, name: str) -> None:
        """Start a single named device."""
        self.get(name).start()

    def start_all(self) -> None:
        """Start all registered devices."""
        for name, proc in self._devices.items():
            try:
                proc.start()
            except Exception as exc:
                print(f"[DeviceManager] Failed to start '{name}': {exc}")

    def close(self, name: str) -> None:
        """Close a single named device."""
        self.get(name).close()

    def close_all(self) -> None:
        """Close all registered devices."""
        for name, proc in list(self._devices.items()):
            try:
                proc.close()
            except Exception as exc:
                print(f"[DeviceManager] Error closing '{name}': {exc}")

    # ------------------------------------------------------------------ #
    # Coordination                                                         #
    # ------------------------------------------------------------------ #

    def send_all(self, cmd: Dict[str, Any]) -> Dict[str, Any]:
        """Send the same command to every connected device.

        Returns a mapping of device name → response dict (or error string).
        """
        results: Dict[str, Any] = {}
        for name, proc in self._devices.items():
            if proc.backend is None:
                results[name] = {"error": "not connected"}
                continue
            try:
                results[name] = proc.backend.send_command(cmd)
            except Exception as exc:
                results[name] = {"error": str(exc)}
        return results

    def step_all(self) -> None:
        """Execute one simulation round on every connected device."""
        for name, proc in self._devices.items():
            if proc.backend is None:
                continue
            try:
                proc.step()
            except Exception as exc:
                print(f"[DeviceManager] step failed for '{name}': {exc}")

    def get_all_states(self) -> Dict[str, Any]:
        """Get current state from every connected device.

        Returns a mapping of device name → SwarmSnapshot (or error string).
        """
        states: Dict[str, Any] = {}
        for name, proc in self._devices.items():
            if proc.backend is None:
                states[name] = {"error": "not connected"}
                continue
            try:
                states[name] = proc.get_state()
            except Exception as exc:
                states[name] = {"error": str(exc)}
        return states

    def total_nodes(self) -> int:
        """Sum of num_nodes across all registered devices."""
        return sum(proc.num_nodes for proc in self._devices.values())

    # ------------------------------------------------------------------ #
    # Context manager                                                      #
    # ------------------------------------------------------------------ #

    def __enter__(self) -> "DeviceManager":
        return self

    def __exit__(self, *args) -> None:
        self.close_all()
