from dataclasses import dataclass
from typing import List

from .node_state import NodeState


@dataclass
class SwarmSnapshot:
    """Snapshot of entire swarm state at a point in time."""

    round_number: int
    time: float
    nodes: List[NodeState]
