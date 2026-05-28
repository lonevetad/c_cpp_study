from pathlib import Path
from typing import Any, Dict, List, Optional

from ._ipc_node_base import _IpcNodeBase
from .swarm_process import SwarmProcess
from .physical_node import PhysicalNode
from .liveness_strategy import LivenessStrategy
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
    """

    def __init__(self):
        self._devices: Dict[str, _IpcNodeBase] = {}

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
                _log.warning("Failed to start '%s': %s", name, exc)

    def connect_all(self) -> None:
        """Connect to all registered physical devices (skips SwarmProcess entries)."""
        for name, device in self._devices.items():
            if not isinstance(device, PhysicalNode):
                continue
            try:
                device.connect()
            except Exception as exc:
                _log.warning("Failed to connect to '%s': %s", name, exc)

    def close(self, name: str) -> None:
        """Close a single named device."""
        self.get(name).close()

    def close_all(self) -> None:
        """Close all registered devices."""
        for name, device in list(self._devices.items()):
            try:
                device.close()
            except Exception as exc:
                _log.warning("Error closing '%s': %s", name, exc)

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
                _log.warning("step failed for '%s': %s", name, exc)

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

    def __enter__(self) -> "DeviceManager":
        return self

    def __exit__(self, *args) -> None:
        self.close_all()
