from pathlib import Path
from typing import Any, Dict, List, Optional

from .swarm_process import SwarmProcess


class DeviceManager:
    """Manage multiple SwarmProcess instances as named devices."""

    def __init__(self):
        self._devices: Dict[str, SwarmProcess] = {}

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

    def send_all(self, cmd: Dict[str, Any]) -> Dict[str, Any]:
        """Send the same command to every connected device."""
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
        """Get current state from every connected device."""
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

    def __enter__(self) -> "DeviceManager":
        return self

    def __exit__(self, *args) -> None:
        self.close_all()
