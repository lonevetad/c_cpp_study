import time
from collections import deque
from typing import List, Optional

from fcpp_bridge.ipc import NodeState, SwarmSnapshot


class StateHistory:
    """Ring-buffer of SwarmSnapshots with monotonic wall-clock timestamps."""

    def __init__(self, max_size: Optional[int] = None):
        self._snapshots: deque = deque(maxlen=max_size)
        self._wall_clocks: deque = deque(maxlen=max_size)
        self._start_wall: Optional[float] = None

    def add(self, snapshot: SwarmSnapshot) -> None:
        now = time.monotonic()
        if self._start_wall is None:
            self._start_wall = now
        self._snapshots.append(snapshot)
        self._wall_clocks.append(now)

    def clear(self) -> None:
        self._snapshots.clear()
        self._wall_clocks.clear()
        self._start_wall = None

    def __len__(self) -> int:
        return len(self._snapshots)

    def get_round(self, index: int) -> SwarmSnapshot:
        """Return snapshot by index; supports negative indexing."""
        return list(self._snapshots)[index]

    def to_list(self) -> List[SwarmSnapshot]:
        return list(self._snapshots)

    def get_node_history(self, node_id: int) -> List[Optional[NodeState]]:
        """Return per-round NodeState for a specific node (None if absent that round)."""
        return [
            next((n for n in s.nodes if n.node_id == node_id), None)
            for s in self._snapshots
        ]
