import threading
from typing import Callable, Dict, Optional

from .ipc_backend import IpcBackend
from .swarm_snapshot import SwarmSnapshot
from .listener_proxy import ListenerProxy
from .updates_listener import UpdatesListener
from .liveness_strategy import LivenessStrategy, PassiveHeartbeatStrategy


class _IpcNodeBase:
    """Shared base for IPC-connected nodes: listener pipeline and liveness monitoring.

    Both SwarmProcess (simulation subprocess) and PhysicalNode (physical device
    deployment) inherit from this class to share listener management, the pluggable
    liveness strategy, and the get_state() pull path.

    Liveness strategy
    -----------------
    The strategy determines how node health is assessed.  It can be set at
    construction time or swapped at runtime::

        node = SwarmProcess(..., liveness_strategy=AlwaysAliveStrategy())
        node.set_liveness_strategy(ActivePingStrategy(lambda: node.backend))

    Built-in strategies: ``PassiveHeartbeatStrategy`` (default),
    ``ActivePingStrategy``, ``AlwaysAliveStrategy``.
    """

    backend: Optional[IpcBackend] = None  # class-level attr for patch.object

    def __init__(
        self,
        listener_mode: str = "sequential",
        liveness_strategy: Optional[LivenessStrategy] = None,
    ) -> None:
        self.backend: Optional[IpcBackend] = None
        self._listener_mode = listener_mode

        # Liveness strategy (pluggable — defaults to passive heartbeat)
        self._liveness_strategy: LivenessStrategy = (
            liveness_strategy if liveness_strategy is not None
            else PassiveHeartbeatStrategy()
        )

        # Liveness monitor thread
        self._heartbeat_thread: Optional[threading.Thread] = None
        self._heartbeat_stop_event: Optional[threading.Event] = None

        # Listener pipeline
        self._global_listener: Optional[ListenerProxy] = None
        self._node_listeners: Dict[int, ListenerProxy] = {}

    # ------------------------------------------------------------------
    # Core IPC operations (shared)
    # ------------------------------------------------------------------

    def get_state(self) -> SwarmSnapshot:
        """Get current node state (pull path; also notifies the liveness strategy)."""
        if not self.backend:
            raise RuntimeError("Not connected")
        snapshot = self.backend.get_state()
        self._update_heartbeats(snapshot)
        return snapshot

    @property
    def node_count(self) -> int:
        """Number of nodes managed by this instance."""
        return 0

    # ------------------------------------------------------------------
    # Liveness strategy management
    # ------------------------------------------------------------------

    def set_liveness_strategy(self, strategy: LivenessStrategy) -> None:
        """Replace the liveness strategy at runtime.

        The old strategy's :meth:`~LivenessStrategy.close` is called before
        the new one is installed, allowing it to release threads or sockets.
        The liveness monitor continues running; its next :meth:`check_liveness`
        call will use the new strategy.

        Example::

            # Switch from passive to active ping at runtime
            node.set_liveness_strategy(
                ActivePingStrategy(backend_getter=lambda: node.backend)
            )
        """
        self._liveness_strategy.close()
        self._liveness_strategy = strategy

    # ------------------------------------------------------------------
    # Backward-compatible _heartbeat_timestamps property
    # ------------------------------------------------------------------

    @property
    def _heartbeat_timestamps(self) -> Dict[int, float]:
        """Mutable reference to the passive strategy's timestamp dict.

        Provided for backward compatibility.  Only meaningful when the active
        liveness strategy is ``PassiveHeartbeatStrategy`` (the default).
        """
        strat = self._liveness_strategy
        if hasattr(strat, "_timestamps"):
            return strat._timestamps  # type: ignore[attr-defined]
        return {}

    # ------------------------------------------------------------------
    # Shared close logic
    # ------------------------------------------------------------------

    def close(self) -> None:
        """Stop liveness monitor, close all listener proxies, and close the backend."""
        self.stop_heartbeat_monitor()
        self._liveness_strategy.close()
        if self._global_listener is not None:
            self._global_listener.close()
        if self.backend is not None:
            self.backend.close()
            self.backend = None

    def __exit__(self, *args) -> None:
        self.close()

    # ------------------------------------------------------------------
    # Liveness / heartbeat
    # ------------------------------------------------------------------

    def _update_heartbeats(self, snapshot: SwarmSnapshot) -> None:
        """Notify the liveness strategy that a snapshot was received."""
        self._liveness_strategy.on_snapshot(snapshot)

    def _discard_node_from_liveness(self, node_id: int) -> None:
        """Remove a node from the liveness strategy's internal tracking.

        Called on explicit node removal so the strategy stops reporting the
        node in future ``check_liveness()`` results.
        """
        self._liveness_strategy.discard(node_id)

    def check_liveness(self, timeout: float = 30.0, **kwargs) -> Dict[int, bool]:
        """Return ``{node_id: alive}`` for all tracked nodes.

        The ``timeout`` kwarg is forwarded to the strategy; ``PassiveHeartbeatStrategy``
        uses it as the liveness window.  Other strategies may use different kwargs
        or ignore ``timeout`` entirely.

        Parameters
        ----------
        timeout : float
            Passed to the strategy's ``check()`` method.  For passive heartbeat
            this is the maximum age (in seconds) of the last received snapshot.
        **kwargs
            Extra keyword arguments forwarded to the strategy unchanged.
        """
        return self._liveness_strategy.check(timeout=timeout, **kwargs)

    def start_heartbeat_monitor(
        self,
        interval: float = 5.0,
        timeout: float = 30.0,
        on_dead: Optional[Callable[[int], None]] = None,
    ) -> None:
        """Start a background thread that calls check_liveness periodically.

        ``on_dead(node_id)`` is called for each node reported as dead on every
        check cycle.  Idempotent: calling again while a monitor is running has
        no effect.

        The ``timeout`` argument is forwarded to :meth:`check_liveness` on every
        tick.  For ``PassiveHeartbeatStrategy`` it is the liveness window; for
        other strategies it may be ignored.
        """
        if self._heartbeat_thread is not None and self._heartbeat_thread.is_alive():
            return
        self._heartbeat_stop_event = threading.Event()
        self._heartbeat_thread = threading.Thread(
            target=self._heartbeat_loop,
            args=(interval, timeout, on_dead),
            daemon=True,
            name=f"{type(self).__name__}-heartbeat",
        )
        self._heartbeat_thread.start()

    def stop_heartbeat_monitor(self) -> None:
        """Stop the liveness monitor background thread (waits up to 2 s)."""
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
            liveness = self.check_liveness(timeout=timeout)
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

    def _dispatch_update(self, snapshot: SwarmSnapshot) -> None:
        """Route an incoming snapshot to the appropriate listener(s).

        Called by the IPC backend's push subscription.
        Also notifies the liveness strategy as a side effect.
        """
        self._update_heartbeats(snapshot)

        for node in snapshot.nodes:
            nid = node.node_id
            if nid in self._node_listeners:
                self._node_listeners[nid](snapshot)
            elif self._global_listener is not None:
                self._global_listener(snapshot)
