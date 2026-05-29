import threading
from typing import Callable, List, Optional

from .http_backend import HttpBackend
from .grpc_backend import GrpcBackend
from .swarm_snapshot import SwarmSnapshot
from .updates_listener import UpdatesListener
from .liveness_strategy import LivenessStrategy
from ._ipc_node_base import _IpcNodeBase
from fcpp_bridge.log import get_logger

_log = get_logger(__name__)


class PhysicalNode(_IpcNodeBase):
    """Connect to and interact with a physical device running a compiled FCPP binary.

    Unlike SwarmProcess, a PhysicalNode does NOT spawn a subprocess.  The device
    is already running on its own hardware (robot, drone, phone, sensor, workstation)
    and Python connects to it via HTTP or gRPC.

    Usage
    -----
    node = PhysicalNode("192.168.1.100", port=50051)
    node.connect()

    # The device runs its own FCPP round loop — no step() call is needed.
    node.add_listener(on_update)
    node.start_heartbeat_monitor(on_dead=on_node_dead)
    node.start_auto_reconnect()   # survives transient link drops

    node.close()   # disconnects Python side; the physical device keeps running

    Neighbor join/leave
    -------------------
    FCPP devices discover their neighbors autonomously via radio.  Python is
    notified through two mechanisms:

    * **on_neighbor_joined(cb)** — cb(node_id) fires when a node_id that has
      never been seen before appears in an incoming SwarmSnapshot.

    * **on_neighbor_left(cb)** — cb(node_id) fires when the heartbeat monitor
      determines that a previously-seen node has been silent for longer than
      the configured timeout.  Requires start_heartbeat_monitor() to be active.
    """

    def __init__(
        self,
        host: str,
        port: int,
        backend_type: str = "http",
        reconnect_interval: float = 5.0,
        listener_mode: str = "sequential",
        liveness_strategy: Optional[LivenessStrategy] = None,
    ) -> None:
        super().__init__(listener_mode=listener_mode, liveness_strategy=liveness_strategy)
        self.host = host
        self.port = port
        self.backend_type = backend_type
        self.reconnect_interval = reconnect_interval

        self._connected: bool = False

        # Auto-reconnect
        self._reconnect_thread: Optional[threading.Thread] = None
        self._reconnect_stop_event: Optional[threading.Event] = None

        # FCPP-level neighbor join/leave callbacks
        self._neighbor_join_callbacks: List[Callable[[int], None]] = []
        self._neighbor_leave_callbacks: List[Callable[[int], None]] = []

        # Node IDs seen so far (for autonomous join detection)
        self._seen_node_ids: set = set()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def __enter__(self) -> "PhysicalNode":
        self.connect()
        return self

    def connect(self) -> None:
        """Connect to the physical device's IPC endpoint.

        Creates the appropriate backend and subscribes to push state updates.
        Safe to call again after a disconnect — the old backend is closed first.
        If the connection attempt fails at any point, the backend is cleaned up
        and ``is_connected`` remains ``False`` (RAII-style reset).
        """
        if self.backend is not None:
            self.backend.close()
            self.backend = None
        self._connected = False  # pessimistic; set True only on full success
        try:
            url = f"http://{self.host}:{self.port}"
            if self.backend_type == "http":
                self.backend = HttpBackend(url)
            elif self.backend_type == "grpc":
                self.backend = GrpcBackend(port=self.port)
            else:
                raise ValueError(
                    f"Unknown backend type: {self.backend_type!r} (choose 'http' or 'grpc')"
                )
            self.backend.subscribe_state_updates(self._dispatch_update)
            self._connected = True
            _log.info("Connected to %s:%s via %s", self.host, self.port, self.backend_type)
        except Exception:
            if self.backend is not None:
                try:
                    self.backend.close()
                except Exception:
                    pass
            self.backend = None
            raise

    def get_state(self):  # type: ignore[override]
        """Get current state, marking the link lost on transport errors."""
        try:
            return super().get_state()
        except (ConnectionError, OSError):
            self._connected = False
            raise

    def close(self) -> None:
        """Disconnect from the device (the physical device keeps running).

        Stops auto-reconnect, stops heartbeat monitor, closes the backend.
        """
        self.stop_auto_reconnect()
        super().close()
        self._connected = False
        _log.info("Disconnected from %s:%s", self.host, self.port)

    @property
    def is_connected(self) -> bool:
        """True if the Python-side connection to the device is currently open."""
        return self._connected

    @property
    def node_count(self) -> int:
        """Number of FCPP neighbor node IDs currently tracked (at least 1)."""
        return len(self._seen_node_ids) or 1

    # ------------------------------------------------------------------
    # Auto-reconnect
    # ------------------------------------------------------------------

    def start_auto_reconnect(self, interval: Optional[float] = None) -> None:
        """Start a background thread that reconnects automatically on connection loss.

        When ``is_connected`` is False the thread calls ``connect()`` every
        ``interval`` seconds until it succeeds.  Idempotent: safe to call while
        already running.
        """
        if self._reconnect_thread is not None and self._reconnect_thread.is_alive():
            return
        if interval is not None:
            self.reconnect_interval = interval
        self._reconnect_stop_event = threading.Event()
        self._reconnect_thread = threading.Thread(
            target=self._reconnect_loop,
            daemon=True,
            name=f"PhysicalNode-reconnect-{self.host}:{self.port}",
        )
        self._reconnect_thread.start()

    def stop_auto_reconnect(self) -> None:
        """Stop the auto-reconnect background thread (waits up to 2 s)."""
        if self._reconnect_stop_event is not None:
            self._reconnect_stop_event.set()
        if self._reconnect_thread is not None:
            self._reconnect_thread.join(timeout=2.0)
            self._reconnect_thread = None
            self._reconnect_stop_event = None

    def _reconnect_loop(self) -> None:
        assert self._reconnect_stop_event is not None
        while not self._reconnect_stop_event.is_set():
            if not self._connected:
                try:
                    self.connect()
                except Exception as exc:
                    _log.warning("Reconnect to %s:%s failed: %s", self.host, self.port, exc)
            self._reconnect_stop_event.wait(self.reconnect_interval)

    # ------------------------------------------------------------------
    # Autonomous neighbor join/leave
    # ------------------------------------------------------------------

    def on_neighbor_joined(self, callback: Callable[[int], None]) -> None:
        """Register a callback fired when a new FCPP neighbor appears in snapshots.

        ``callback(node_id)`` is called from the listener dispatch thread the
        first time ``node_id`` is seen in any incoming SwarmSnapshot.
        """
        self._neighbor_join_callbacks.append(callback)

    def on_neighbor_left(self, callback: Callable[[int], None]) -> None:
        """Register a callback fired when a tracked neighbor is declared dead.

        Requires ``start_heartbeat_monitor()`` to be active.  The callback is
        invoked from the heartbeat thread when a node exceeds the liveness timeout.
        """
        self._neighbor_leave_callbacks.append(callback)

    def start_heartbeat_monitor(
        self,
        interval: float = 5.0,
        timeout: float = 30.0,
        on_dead: Optional[Callable[[int], None]] = None,
    ) -> None:
        """Start heartbeat monitor; also triggers on_neighbor_left callbacks.

        Overrides the base-class method to compose the user-supplied on_dead
        with any registered on_neighbor_left callbacks.
        """
        def _combined_on_dead(nid: int) -> None:
            self._seen_node_ids.discard(nid)
            for cb in self._neighbor_leave_callbacks:
                cb(nid)
            if on_dead is not None:
                on_dead(nid)

        super().start_heartbeat_monitor(interval, timeout, _combined_on_dead)

    # ------------------------------------------------------------------
    # Override _dispatch_update to detect autonomous joins
    # ------------------------------------------------------------------

    def _dispatch_update(self, snapshot: SwarmSnapshot) -> None:
        """Detect new neighbors, then dispatch to listeners.

        First time a node_id appears in any snapshot the on_neighbor_joined
        callbacks are fired.  Then the normal listener dispatch runs.
        """
        for node in snapshot.nodes:
            nid = node.node_id
            if nid not in self._seen_node_ids:
                self._seen_node_ids.add(nid)
                for cb in self._neighbor_join_callbacks:
                    cb(nid)

        super()._dispatch_update(snapshot)
