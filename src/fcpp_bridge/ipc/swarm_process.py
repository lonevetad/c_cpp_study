import random
import subprocess
import time
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

from .ipc_backend import IpcBackend
from .unix_socket_backend import UnixSocketBackend
from .http_backend import HttpBackend
from .grpc_backend import GrpcBackend
from .swarm_snapshot import SwarmSnapshot
from .updates_listener import UpdatesListener
from .liveness_strategy import LivenessStrategy
from ._ipc_node_base import _IpcNodeBase
from fcpp_bridge.log import get_logger

_log = get_logger(__name__)


class SwarmProcess(_IpcNodeBase):
    """Manage a compiled swarm subprocess with IPC communication.

    This class is for **simulation mode**: it spawns a local C++ binary and
    drives the entire swarm from Python.  For deploying to physical devices
    (robots, drones, phones, sensors) see :class:`PhysicalNode`.

    Node addition strategies
    ------------------------
    add_nodes_random(count, ...)      random unique IDs
    add_node_explicit(id, pos, ...)   explicit ID + position
    add_nodes_sequential(count, ...)  sequential IDs (unique by construction)
    add_nodes(count)                  backward-compat alias for add_nodes_sequential

    Node removal
    ------------
    remove_node(node_id)

    Liveness / heartbeat
    --------------------
    Passive heartbeat: a node is considered alive if a SwarmSnapshot containing
    its ID was received within the timeout window.

    check_liveness(timeout)                     → Dict[int, bool]
    start_heartbeat_monitor(interval, timeout)  background thread
    stop_heartbeat_monitor()

    Updates listener pipeline
    -------------------------
    add_listener(fn)                → int  (global; auto-creates ListenerProxy)
    remove_listener(listener_id)
    add_node_listener(node_id, fn)  → int  (per-node override)
    remove_node_listener(node_id, listener_id)

    Dispatch order: if a node has a per-node listener, that listener is called
    instead of the global listener.
    """

    backend: Optional[IpcBackend] = None  # class-level attr required for patch.object

    def __init__(
        self,
        binary_path: Path,
        num_nodes: int = 100,
        ipc_backend: str = "unix",
        ipc_port: Optional[int] = None,
        listener_mode: str = "sequential",
        liveness_strategy: Optional[LivenessStrategy] = None,
    ):
        super().__init__(listener_mode=listener_mode, liveness_strategy=liveness_strategy)
        self.binary_path = Path(binary_path)
        self.num_nodes = num_nodes
        self.ipc_backend_name = ipc_backend
        self.ipc_port = ipc_port or 50051
        self.process: Optional[subprocess.Popen] = None

        # Node ID tracking
        self._known_node_ids: set = set()
        self._next_sequential_id: int = 0

        # Latest snapshot from the most recent update
        self._latest_snapshot: Optional[SwarmSnapshot] = None

    @property
    def node_count(self) -> int:
        return self.num_nodes

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def __enter__(self):
        self.start()
        return self

    def start(self) -> None:
        """Start the swarm subprocess."""
        if not self.binary_path.exists():
            raise FileNotFoundError(f"Binary not found: {self.binary_path}")

        _log.info("Starting %s", self.binary_path)

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

        # Assume initial nodes got sequential IDs 0 .. num_nodes-1
        self._known_node_ids = set(range(self.num_nodes))
        self._next_sequential_id = self.num_nodes

        # Wire push subscription to the dispatch pipeline
        self.backend.subscribe_state_updates(self._dispatch_update)

    def _create_backend(self) -> None:
        if self.ipc_backend_name == "unix":
            self.backend = UnixSocketBackend()
        elif self.ipc_backend_name.startswith("http://"):
            self.backend = HttpBackend(self.ipc_backend_name)
        elif self.ipc_backend_name == "grpc":
            self.backend = GrpcBackend(port=self.ipc_port)
        else:
            raise ValueError(f"Unknown IPC backend: {self.ipc_backend_name}")

        _log.info("Connected via %s", self.ipc_backend_name)

    def close(self) -> None:
        """Stop swarm subprocess and cleanup."""
        super().close()  # stops heartbeat, closes listener proxy, closes backend

        if self.process:
            self.process.terminate()
            try:
                self.process.wait(timeout=5.0)
            except subprocess.TimeoutExpired:
                self.process.kill()
            self.process = None

        _log.info("Closed")

    # ------------------------------------------------------------------
    # Core IPC operations
    # ------------------------------------------------------------------

    def latest_snapshot(self) -> Optional[SwarmSnapshot]:
        """Return the snapshot from the most recent update, or None before the first step."""
        return self._latest_snapshot

    def _dispatch_update(self, snapshot: SwarmSnapshot) -> None:
        self._latest_snapshot = snapshot
        super()._dispatch_update(snapshot)

    def step(self) -> None:
        """Execute one simulation round."""
        if not self.backend:
            raise RuntimeError("Not connected")
        self.backend.send_command({"cmd": "step"})

    # ------------------------------------------------------------------
    # Node addition — three strategies
    # ------------------------------------------------------------------

    def add_nodes_random(
        self,
        count: int,
        *,
        area: Optional[Tuple] = None,
        comm_range: Optional[float] = None,
        max_speed: Optional[float] = None,
        propulsion: Optional[float] = None,
    ) -> List[int]:
        """Add *count* nodes with random unique IDs.

        Optional keyword arguments are forwarded to the C++ binary:
            area        — bounding box (xmin,ymin,xmax,ymax) for random placement
            comm_range  — communication radius
            max_speed   — maximum movement speed
            propulsion  — propulsion force
        """
        if not self.backend:
            raise RuntimeError("Not connected")

        node_ids: List[int] = []
        while len(node_ids) < count:
            nid = random.randint(0, 2**31 - 1)
            if nid not in self._known_node_ids:
                node_ids.append(nid)
                self._known_node_ids.add(nid)

        def _node_entry(nid: int) -> dict:
            entry: dict = {"id": nid}
            if area is not None:
                entry["area"] = list(area)
            if comm_range is not None:
                entry["comm_range"] = comm_range
            if max_speed is not None:
                entry["max_speed"] = max_speed
            if propulsion is not None:
                entry["propulsion"] = propulsion
            return entry

        self.backend.send_command({
            "cmd": "add_nodes",
            "nodes": [_node_entry(nid) for nid in node_ids],
        })
        self.num_nodes += count
        return node_ids

    def add_node_explicit(
        self,
        node_id: int,
        position: Tuple,
        *,
        comm_range: Optional[float] = None,
        max_speed: Optional[float] = None,
        propulsion: Optional[float] = None,
    ) -> None:
        """Add a single node with an explicit ID and position.

        Intended for registering realistic or physical devices whose ID and
        location are known in advance.  Raises ValueError if the ID is already
        in use.
        """
        if not self.backend:
            raise RuntimeError("Not connected")
        if node_id in self._known_node_ids:
            raise ValueError(f"Node ID {node_id} is already in use")

        self._known_node_ids.add(node_id)
        cmd: dict = {
            "cmd": "add_node",
            "id": node_id,
            "position": list(position),
        }
        if comm_range is not None:
            cmd["comm_range"] = comm_range
        if max_speed is not None:
            cmd["max_speed"] = max_speed
        if propulsion is not None:
            cmd["propulsion"] = propulsion

        self.backend.send_command(cmd)
        self.num_nodes += 1

    def add_nodes_sequential(
        self,
        count: int,
        start_positions: Optional[List[Tuple]] = None,
    ) -> List[int]:
        """Add *count* nodes with automatically assigned sequential IDs.

        IDs are unique by construction (monotonically increasing counter).
        Optional start_positions[i] sets the initial position of the i-th
        new node; extra or missing positions are silently ignored/omitted.
        """
        if not self.backend:
            raise RuntimeError("Not connected")

        node_ids: List[int] = []
        for _ in range(count):
            nid = self._next_sequential_id
            self._next_sequential_id += 1
            self._known_node_ids.add(nid)
            node_ids.append(nid)

        nodes = [{"id": nid} for nid in node_ids]
        if start_positions:
            for i, pos in enumerate(start_positions[:len(nodes)]):
                nodes[i]["position"] = list(pos)

        self.backend.send_command({"cmd": "add_nodes", "nodes": nodes})
        self.num_nodes += count
        return node_ids

    def add_nodes(self, count: int) -> None:
        """Add *count* nodes (backward-compatible; delegates to add_nodes_sequential)."""
        if not self.backend:
            raise RuntimeError("Not connected")
        self.add_nodes_sequential(count)

    # ------------------------------------------------------------------
    # Node removal
    # ------------------------------------------------------------------

    def remove_node(self, node_id: int) -> None:
        """Remove a node by ID (simulation disconnection).

        Raises ValueError if the node ID is not tracked.
        """
        if not self.backend:
            raise RuntimeError("Not connected")
        if node_id not in self._known_node_ids:
            raise ValueError(f"Node ID {node_id} is not tracked")

        self._known_node_ids.discard(node_id)
        self._discard_node_from_liveness(node_id)
        self._node_listeners.pop(node_id, None)
        self.backend.send_command({"cmd": "remove_node", "id": node_id})
        self.num_nodes = max(0, self.num_nodes - 1)
