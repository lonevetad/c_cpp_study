from dataclasses import dataclass
from typing import Any


@dataclass
class NodeState:
    """State of a single node in the swarm."""

    node_id: int
    state_data: Any
    timestamp: float
