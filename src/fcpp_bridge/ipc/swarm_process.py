import subprocess
import time
from pathlib import Path
from typing import Optional

from .ipc_backend import IpcBackend
from .unix_socket_backend import UnixSocketBackend
from .http_backend import HttpBackend
from .grpc_backend import GrpcBackend
from .swarm_snapshot import SwarmSnapshot


class SwarmProcess:
    """Manages a compiled swarm subprocess with IPC communication."""

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
        self.start()
        return self

    def __exit__(self, *args):
        self.close()

    def start(self) -> None:
        """Start the swarm subprocess."""
        if not self.binary_path.exists():
            raise FileNotFoundError(f"Binary not found: {self.binary_path}")

        print(f"[SwarmProcess] Starting {self.binary_path}")

        try:
            self.process = subprocess.Popen(
                [str(self.binary_path), f"--num-nodes={self.num_nodes}"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
        except Exception as e:
            raise RuntimeError(f"Failed to start swarm process: {e}")

        time.sleep(0.5)
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
