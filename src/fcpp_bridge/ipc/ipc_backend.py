from abc import ABC, abstractmethod
from typing import Any, Callable, Dict

from .swarm_snapshot import SwarmSnapshot


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
        """Subscribe to continuous state updates (optional; default: noop)."""

    @abstractmethod
    def close(self) -> None:
        """Close connection."""
        pass
