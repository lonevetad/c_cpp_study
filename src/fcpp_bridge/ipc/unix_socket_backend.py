import json
import socket
from pathlib import Path
from typing import Any, Dict, Optional

from .ipc_backend import IpcBackend
from .node_state import NodeState
from .swarm_snapshot import SwarmSnapshot


class UnixSocketBackend(IpcBackend):
    """Unix socket backend (default)."""

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

        request = json.dumps(cmd).encode() + b"\n"

        try:
            self.sock.sendall(request)

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
