from typing import Any, Dict

from .ipc_backend import IpcBackend
from .node_state import NodeState
from .swarm_snapshot import SwarmSnapshot


class HttpBackend(IpcBackend):
    """HTTP/REST backend."""

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
