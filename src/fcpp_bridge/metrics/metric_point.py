from dataclasses import dataclass
from typing import List


@dataclass
class MetricPoint:
    """One metrics observation at a single simulation round."""

    round_number: int
    sim_time: float
    wall_clock: float
    node_count: int
    numeric_values: List[float]
