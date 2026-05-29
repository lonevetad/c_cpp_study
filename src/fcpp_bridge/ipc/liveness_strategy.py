"""Pluggable liveness strategies for determining node health.

The Strategy pattern decouples *how* a node is declared alive or dead from
the machinery that runs the periodic monitor.  The built-in strategies cover
the common cases; custom strategies can be passed to ``_IpcNodeBase.__init__``
or swapped at runtime via ``set_liveness_strategy()``.

Built-in strategies
-------------------
PassiveHeartbeatStrategy
    Alive if a snapshot containing the node was received within ``timeout``
    seconds.  No messages are sent; zero C++ runtime requirements.
    Default when no strategy is specified.

ActivePingStrategy
    Alive if the node replies ``{"status": "pong"}`` to a
    ``{"cmd": "ping", "node_id": <id>}`` command within ``ping_timeout``
    seconds.  The ping handler is registered automatically by the standard
    ``SwarmSimulator`` C++ template (see ``RuntimeGenerator.main_template_header``).

AlwaysAliveStrategy
    Every known node is always alive.  Useful for testing, fixed sensor grids,
    or disabling liveness checks without removing the monitor thread.
"""

import time
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, Optional

from .swarm_snapshot import SwarmSnapshot


class LivenessStrategy(ABC):
    """Abstract base for node liveness detection.

    Implementations are notified of every received snapshot via
    :meth:`on_snapshot` and are queried for liveness via :meth:`check`.

    Unknown keyword arguments passed to :meth:`check` must be silently ignored
    for forward compatibility — new callers may pass extra hints that older
    strategies do not understand.
    """

    @abstractmethod
    def on_snapshot(self, snapshot: SwarmSnapshot) -> None:
        """Called every time a snapshot is received (push or pull path).

        Use this to update internal tracking state, e.g. record timestamps or
        note which node IDs exist.
        """

    @abstractmethod
    def check(self, **kwargs) -> Dict[int, bool]:
        """Return ``{node_id: alive}`` for all currently tracked nodes.

        Keyword arguments are strategy-specific; see each implementation for
        the parameters it accepts.  Unknown kwargs must be ignored silently.
        """

    def discard(self, node_id: int) -> None:
        """Remove a node from this strategy's internal tracking.

        Called on explicit node removal (e.g. ``SwarmProcess.remove_node``).
        Default is a no-op; override if the strategy maintains per-node state.
        """

    def close(self) -> None:
        """Release any resources held by this strategy (threads, sockets, …).

        Called when the owning node is closed or when the strategy is replaced
        via :meth:`_IpcNodeBase.set_liveness_strategy`.  Default is a no-op.
        """


# ---------------------------------------------------------------------------
# PassiveHeartbeatStrategy
# ---------------------------------------------------------------------------


class PassiveHeartbeatStrategy(LivenessStrategy):
    """Passive liveness: alive if a snapshot was received within ``timeout`` s.

    No outbound messages are sent to the node.  Liveness is inferred purely
    from whether the node keeps appearing in incoming ``SwarmSnapshot`` objects.
    This is the simplest and most portable strategy — it works with every IPC
    backend and requires no changes to the compiled C++ binary.

    Parameters
    ----------
    timeout : float
        Default liveness window in seconds.  Can be overridden per-call by
        passing ``timeout=<value>`` to :meth:`check`.
    """

    def __init__(self, timeout: float = 30.0) -> None:
        self.timeout = timeout
        self._timestamps: Dict[int, float] = {}

    def on_snapshot(self, snapshot: SwarmSnapshot) -> None:
        now = time.time()
        for node in snapshot.nodes:
            self._timestamps[node.node_id] = now

    def check(self, timeout: Optional[float] = None, **_kwargs) -> Dict[int, bool]:
        """Return liveness for all tracked nodes.

        Parameters
        ----------
        timeout : float, optional
            Override ``self.timeout`` for this call only.
        """
        t = timeout if timeout is not None else self.timeout
        now = time.time()
        return {nid: (now - ts) <= t for nid, ts in self._timestamps.items()}

    def discard(self, node_id: int) -> None:
        self._timestamps.pop(node_id, None)


# ---------------------------------------------------------------------------
# ActivePingStrategy
# ---------------------------------------------------------------------------


class ActivePingStrategy(LivenessStrategy):
    """Active liveness: alive if the node replies to an explicit ping.

    Sends ``{"cmd": "ping", "node_id": <id>}`` via the IPC backend and
    expects ``{"status": "pong"}`` in the response within ``ping_timeout``
    seconds.

    The ``ping`` handler is registered automatically by the ``SwarmSimulator``
    constructor in ``main_template.hpp`` (generated by ``RuntimeGenerator``).
    No manual C++ changes are required for binaries built with the standard
    template.

    Parameters
    ----------
    backend_getter : Callable[[], Optional[IpcBackend]]
        Called at check time to get the current backend.  Use a lambda so the
        strategy always sees the latest backend even after reconnects, e.g.::

            ActivePingStrategy(backend_getter=lambda: node.backend)

    ping_timeout : float
        Seconds to wait for a pong response per node.
    """

    def __init__(
        self,
        backend_getter: Callable[[], Any],
        ping_timeout: float = 2.0,
    ) -> None:
        self._get_backend = backend_getter
        self.ping_timeout = ping_timeout
        self._known_ids: set = set()

    def on_snapshot(self, snapshot: SwarmSnapshot) -> None:
        for node in snapshot.nodes:
            self._known_ids.add(node.node_id)

    def check(self, ping_timeout: Optional[float] = None, **_kwargs) -> Dict[int, bool]:
        """Ping every known node and return whether it responded.

        Parameters
        ----------
        ping_timeout : float, optional
            Override ``self.ping_timeout`` for this call only.
        """
        backend = self._get_backend()
        if backend is None:
            return {nid: False for nid in self._known_ids}

        t = ping_timeout if ping_timeout is not None else self.ping_timeout
        result: Dict[int, bool] = {}
        for nid in list(self._known_ids):
            try:
                resp = backend.send_command(
                    {"cmd": "ping", "node_id": nid, "timeout": t}
                )
                result[nid] = resp.get("status") == "pong"
            except Exception:
                result[nid] = False
        return result

    def discard(self, node_id: int) -> None:
        self._known_ids.discard(node_id)


# ---------------------------------------------------------------------------
# AlwaysAliveStrategy
# ---------------------------------------------------------------------------


class AlwaysAliveStrategy(LivenessStrategy):
    """Liveness strategy that reports every known node as alive.

    Useful for:

    * **Testing** — disable liveness checks without removing the monitor thread.
    * **Fixed topologies** — sensor grids or wired networks where nodes never leave.
    * **Development** — run without worrying about heartbeat timeouts.
    """

    def __init__(self) -> None:
        self._known_ids: set = set()

    def on_snapshot(self, snapshot: SwarmSnapshot) -> None:
        for node in snapshot.nodes:
            self._known_ids.add(node.node_id)

    def check(self, **_kwargs) -> Dict[int, bool]:
        return {nid: True for nid in self._known_ids}

    def discard(self, node_id: int) -> None:
        self._known_ids.discard(node_id)
