import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Optional

from .updates_listener import UpdatesListener
from .swarm_snapshot import SwarmSnapshot


class ListenerProxy:
    """Dispatch swarm state updates to a dynamic list of listeners.

    mode="sequential"  — call each listener in insertion order (default).
    mode="parallel"    — submit each listener to a thread pool concurrently.

    Listener IDs are monotonically increasing integers returned by
    add_listener(); callers must store the ID to be able to remove that
    listener later.
    """

    def __init__(self, mode: str = "sequential") -> None:
        if mode not in ("sequential", "parallel"):
            raise ValueError(f"mode must be 'sequential' or 'parallel', got {mode!r}")
        self._mode = mode
        self._listeners: Dict[int, UpdatesListener] = {}
        self._next_id: int = 0
        self._lock = threading.Lock()
        self._executor: Optional[ThreadPoolExecutor] = None
        if mode == "parallel":
            self._executor = ThreadPoolExecutor()

    # ------------------------------------------------------------------
    # Listener registration
    # ------------------------------------------------------------------

    def add_listener(self, listener: UpdatesListener) -> int:
        """Register listener; return its integer ID."""
        with self._lock:
            lid = self._next_id
            self._next_id += 1
            self._listeners[lid] = listener
        return lid

    def remove_listener(self, listener_id: int) -> None:
        """Remove a previously registered listener by ID."""
        with self._lock:
            if listener_id not in self._listeners:
                raise KeyError(f"No listener with ID {listener_id}")
            del self._listeners[listener_id]

    # ------------------------------------------------------------------
    # Dispatch
    # ------------------------------------------------------------------

    def __call__(self, snapshot: SwarmSnapshot) -> None:
        """Dispatch snapshot to all registered listeners."""
        with self._lock:
            listeners = list(self._listeners.values())
        if self._mode == "sequential":
            for fn in listeners:
                fn(snapshot)
        else:
            for fn in listeners:
                self._executor.submit(fn, snapshot)

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    @property
    def mode(self) -> str:
        return self._mode

    def __len__(self) -> int:
        return len(self._listeners)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def close(self) -> None:
        """Shut down the thread pool (only relevant in parallel mode)."""
        if self._executor is not None:
            self._executor.shutdown(wait=False)
            self._executor = None
