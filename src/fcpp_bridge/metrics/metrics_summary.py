from dataclasses import dataclass
from typing import List


@dataclass
class MetricsSummary:
    """Statistical summary over all collected rounds."""

    total_rounds: int
    total_sim_time: float
    total_wall_time: float
    avg_node_count: float
    mean_per_round: List[float]
    min_per_round: List[float]
    max_per_round: List[float]
    std_per_round: List[float]
