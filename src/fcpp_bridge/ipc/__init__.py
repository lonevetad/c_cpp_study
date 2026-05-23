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
                state_data=n["state"],
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
                state_data=n["state"],
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
    """
    gRPC backend for streaming state updates.

    Requires: pip install grpcio
    """

    def __init__(self, host: str = "localhost", port: int = 50051):
        self.host = host
        self.port = port
        self.channel = None
        self.stub = None
        self._connect()

    def _connect(self) -> None:
        """Connect to gRPC server."""
        try:
            import grpc

            self.channel = grpc.aio.secure_channel(f"{self.host}:{self.port}")
            # Stub creation would go here (requires .proto definitions)
        except ImportError:
            raise RuntimeError("grpcio library not installed; install with: pip install grpcio")

    def send_command(self, cmd: Dict[str, Any]) -> Dict[str, Any]:
        """Send command via gRPC."""
        raise NotImplementedError("Phase 6: gRPC backend full implementation pending")

    def get_state(self) -> SwarmSnapshot:
        """Get state via gRPC streaming."""
        raise NotImplementedError("Phase 6: gRPC backend full implementation pending")

    def close(self) -> None:
        """Close gRPC channel."""
        if self.channel:
            # self.channel.close()
            pass


class SwarmProcess:
    """
    Manages a compiled swarm subprocess with IPC communication.

    Usage:
        swarm = SwarmProcess(binary_path, ipc_backend="unix")
        swarm.step()
        state = swarm.get_state()
        swarm.close()
    """

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
