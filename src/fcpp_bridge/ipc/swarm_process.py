import random
import subprocess
import threading
import time
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

from .ipc_backend import IpcBackend
from .unix_socket_backend import UnixSocketBackend
from .http_backend import HttpBackend
from .grpc_backend import GrpcBackend
from .swarm_snapshot import SwarmSnapshot
from .listener_proxy import ListenerProxy
from .updates_listener import UpdatesListener


class SwarmProcess:
    """Manage a compiled swarm subprocess with IPC communication.

    Node addition strategies
    ------------------------
    add_nodes_random(count, ...)      random unique IDs
    add_node_explicit(id, pos, ...)   explicit ID + position (physical devices)
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
    ):
        self.binary_path = Path(binary_path)
        self.num_nodes = num_nodes
        self.ipc_backend_name = ipc_backend
        self.ipc_port = ipc_port or 50051
        self._listener_mode = listener_mode
        self.process: Optional[subprocess.Popen] = None
        self.backend: Optional[IpcBackend] = None

        # Node ID tracking
        self._known_node_ids: set = set()
        self._next_sequential_id: int = 0

        # Heartbeat (passive): node_id → last-seen timestamp
        self._heartbeat_timestamps: Dict[int, float] = {}
        self._heartbeat_thread: Optional[threading.Thread] = None
        self._heartbeat_stop_event: Optional[threading.Event] = None

        # Listener pipeline
        self._global_listener: Optional[ListenerProxy] = None
        self._node_listeners: Dict[int, ListenerProxy] = {}

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

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

        # Assume initial nodes got sequential IDs 0 .. num_nodes-1
        self._known_node_ids = set(range(self.num_nodes))
        self._next_sequential_id = self.num_nodes

        # Wire push subscription to the dispatch pipeline
        self.backend.subscribe_state_updates(self._dispatch_update)

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

    def close(self) -> None:
        """Stop swarm and cleanup."""
        self.stop_heartbeat_monitor()

        if self._global_listener is not None:
            self._global_listener.close()

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

    # ------------------------------------------------------------------
    # Core IPC operations
    # ------------------------------------------------------------------

    def step(self) -> None:
        """Execute one simulation round."""
        if not self.backend:
            raise RuntimeError("Not connected")
        self.backend.send_command({"cmd": "step"})

    def get_state(self) -> SwarmSnapshot:
        """Get current swarm state (pull path; also updates heartbeat timestamps)."""
        if not self.backend:
            raise RuntimeError("Not connected")
        snapshot = self.backend.get_state()
        self._update_heartbeats(snapshot)
        return snapshot

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
        self._heartbeat_timestamps.pop(node_id, None)
        self._node_listeners.pop(node_id, None)
        self.backend.send_command({"cmd": "remove_node", "id": node_id})
        self.num_nodes = max(0, self.num_nodes - 1)

    # ------------------------------------------------------------------
    # Liveness / heartbeat
    # ------------------------------------------------------------------

    def _update_heartbeats(self, snapshot: SwarmSnapshot) -> None:
        """Record the current time as the last-seen timestamp for each node."""
        now = time.time()
        for node in snapshot.nodes:
            self._heartbeat_timestamps[node.node_id] = now

    def check_liveness(self, timeout: float = 30.0) -> Dict[int, bool]:
        """Return {node_id: True} for each tracked node seen within *timeout* seconds."""
        now = time.time()
        return {
            nid: (now - ts) <= timeout
            for nid, ts in self._heartbeat_timestamps.items()
        }

    def start_heartbeat_monitor(
        self,
        interval: float = 5.0,
        timeout: float = 30.0,
        on_dead: Optional[Callable[[int], None]] = None,
    ) -> None:
        """Start a background thread that calls check_liveness periodically.

        on_dead(node_id) is called once per dead node per check cycle.
        Idempotent: calling again while a monitor is running has no effect.
        """
        if self._heartbeat_thread is not None and self._heartbeat_thread.is_alive():
            return
        self._heartbeat_stop_event = threading.Event()
        self._heartbeat_thread = threading.Thread(
            target=self._heartbeat_loop,
            args=(interval, timeout, on_dead),
            daemon=True,
            name="SwarmProcess-heartbeat",
        )
        self._heartbeat_thread.start()

    def stop_heartbeat_monitor(self) -> None:
        """Stop the heartbeat background thread (waits up to 2 s)."""
        if self._heartbeat_stop_event is not None:
            self._heartbeat_stop_event.set()
        if self._heartbeat_thread is not None:
            self._heartbeat_thread.join(timeout=2.0)
            self._heartbeat_thread = None
            self._heartbeat_stop_event = None

    def _heartbeat_loop(
        self,
        interval: float,
        timeout: float,
        on_dead: Optional[Callable[[int], None]],
    ) -> None:
        assert self._heartbeat_stop_event is not None
        while not self._heartbeat_stop_event.is_set():
            liveness = self.check_liveness(timeout)
            if on_dead is not None:
                for nid, alive in liveness.items():
                    if not alive:
                        on_dead(nid)
            self._heartbeat_stop_event.wait(interval)

    # ------------------------------------------------------------------
    # Updates listener pipeline
    # ------------------------------------------------------------------

    def add_listener(self, listener: UpdatesListener) -> int:
        """Register a global updates listener.

        If this is the first listener, a ListenerProxy is created using the
        mode passed to __init__ (default "sequential").
        Returns the listener ID for later removal.
        """
        if self._global_listener is None:
            self._global_listener = ListenerProxy(mode=self._listener_mode)
        return self._global_listener.add_listener(listener)

    def remove_listener(self, listener_id: int) -> None:
        """Remove a global listener by ID."""
        if self._global_listener is None:
            raise RuntimeError("No listeners registered")
        self._global_listener.remove_listener(listener_id)

    def add_node_listener(self, node_id: int, listener: UpdatesListener) -> int:
        """Register a per-node listener that overrides the global listener.

        Returns the listener ID for later removal via remove_node_listener.
        """
        if node_id not in self._node_listeners:
            self._node_listeners[node_id] = ListenerProxy(mode=self._listener_mode)
        return self._node_listeners[node_id].add_listener(listener)

    def remove_node_listener(self, node_id: int, listener_id: int) -> None:
        """Remove a per-node listener by node ID and listener ID."""
        proxy = self._node_listeners.get(node_id)
        if proxy is None:
            raise RuntimeError(f"No per-node listeners for node {node_id}")
        proxy.remove_listener(listener_id)

    # ------------------------------------------------------------------
    # Internal dispatch
    # ------------------------------------------------------------------

    def _dispatch_update(self, snapshot: SwarmSnapshot) -> None:
        """Route an incoming snapshot to the appropriate listener(s).

        Called by the IPC backend's push subscription and also wired to
        the pull path via get_state().
        Updates heartbeat timestamps as a side effect.
        """
        self._update_heartbeats(snapshot)

        for node in snapshot.nodes:
            nid = node.node_id
            if nid in self._node_listeners:
                self._node_listeners[nid](snapshot)
            elif self._global_listener is not None:
                self._global_listener(snapshot)
