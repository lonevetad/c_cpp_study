"""Metrics collection — capture and analyze swarm state over time (Phase 6)."""

from pathlib import Path
from typing import List, Optional, Callable, Any
from dataclasses import dataclass, field
from collections import deque
import json
import csv
import time
import statistics

from fcpp_bridge.ipc import SwarmSnapshot, NodeState


@dataclass
class MetricPoint:
    """One metrics observation at a single simulation round."""

    round_number: int
    sim_time: float
    wall_clock: float
    node_count: int
    numeric_values: List[float]


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


def _default_extractor(node: NodeState) -> float:
    """Try to interpret state_data as a float."""
    if node.state_data is None:
        return 0.0
    return float(node.state_data)


class MetricsCollector:
    """Collect, analyze, and export swarm metrics over time.

    Phase 6 deliverable: captures state history for 1000-node swarms,
    computes per-round statistics, and exports to JSON/CSV.
    """

    def __init__(
        self,
        history_size: Optional[int] = 10_000,
        state_extractor: Optional[Callable[[NodeState], float]] = None,
    ):
        """
        Args:
            history_size: Max snapshots to retain (None = unlimited).
            state_extractor: Extracts a float from a NodeState for statistics.
        """
        self.history = StateHistory(max_size=history_size)
        self._extractor = state_extractor or _default_extractor
        self._callbacks: List[Callable[[SwarmSnapshot], None]] = []
        self._points: deque = deque(maxlen=history_size)

    # ------------------------------------------------------------------
    # Recording
    # ------------------------------------------------------------------

    def record(self, snapshot: SwarmSnapshot) -> None:
        """Record one snapshot; fires registered callbacks."""
        self.history.add(snapshot)

        numeric_values: List[float] = []
        for node in snapshot.nodes:
            try:
                numeric_values.append(self._extractor(node))
            except (TypeError, ValueError, KeyError):
                pass

        point = MetricPoint(
            round_number=snapshot.round_number,
            sim_time=snapshot.time,
            wall_clock=time.monotonic(),
            node_count=len(snapshot.nodes),
            numeric_values=numeric_values,
        )
        self._points.append(point)

        for cb in self._callbacks:
            cb(snapshot)

    # ------------------------------------------------------------------
    # Callback management
    # ------------------------------------------------------------------

    def on_update(self, callback: Callable[[SwarmSnapshot], None]) -> None:
        """Register a callback invoked on each new snapshot."""
        self._callbacks.append(callback)

    def remove_callback(self, callback: Callable) -> None:
        """Remove a previously registered callback."""
        self._callbacks = [c for c in self._callbacks if c is not callback]

    # ------------------------------------------------------------------
    # Analysis
    # ------------------------------------------------------------------

    def summarize(self) -> MetricsSummary:
        """Compute aggregate statistics over all collected rounds."""
        points = list(self._points)
        if not points:
            return MetricsSummary(
                total_rounds=0,
                total_sim_time=0.0,
                total_wall_time=0.0,
                avg_node_count=0.0,
                mean_per_round=[],
                min_per_round=[],
                max_per_round=[],
                std_per_round=[],
            )

        total_sim_time = (
            points[-1].sim_time - points[0].sim_time if len(points) > 1 else 0.0
        )
        total_wall_time = (
            points[-1].wall_clock - points[0].wall_clock if len(points) > 1 else 0.0
        )
        avg_node_count = statistics.mean(p.node_count for p in points)

        mean_per_round, min_per_round, max_per_round, std_per_round = [], [], [], []
        for p in points:
            if p.numeric_values:
                mean_per_round.append(statistics.mean(p.numeric_values))
                min_per_round.append(min(p.numeric_values))
                max_per_round.append(max(p.numeric_values))
                std_per_round.append(
                    statistics.stdev(p.numeric_values)
                    if len(p.numeric_values) > 1
                    else 0.0
                )
            else:
                mean_per_round.append(0.0)
                min_per_round.append(0.0)
                max_per_round.append(0.0)
                std_per_round.append(0.0)

        return MetricsSummary(
            total_rounds=len(points),
            total_sim_time=total_sim_time,
            total_wall_time=total_wall_time,
            avg_node_count=avg_node_count,
            mean_per_round=mean_per_round,
            min_per_round=min_per_round,
            max_per_round=max_per_round,
            std_per_round=std_per_round,
        )

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    def export_json(self, path: Path) -> None:
        """Export metrics history to a JSON file."""
        data = {
            "rounds": [
                {
                    "round": p.round_number,
                    "sim_time": p.sim_time,
                    "wall_clock": p.wall_clock,
                    "node_count": p.node_count,
                    "mean": statistics.mean(p.numeric_values) if p.numeric_values else None,
                    "min": min(p.numeric_values) if p.numeric_values else None,
                    "max": max(p.numeric_values) if p.numeric_values else None,
                }
                for p in self._points
            ]
        }
        Path(path).write_text(json.dumps(data, indent=2))

    def export_csv(self, path: Path) -> None:
        """Export metrics history to a CSV file."""
        with open(path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["round", "sim_time", "wall_clock", "node_count", "mean", "min", "max"])
            for p in self._points:
                writer.writerow([
                    p.round_number,
                    p.sim_time,
                    p.wall_clock,
                    p.node_count,
                    statistics.mean(p.numeric_values) if p.numeric_values else "",
                    min(p.numeric_values) if p.numeric_values else "",
                    max(p.numeric_values) if p.numeric_values else "",
                ])

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    def clear(self) -> None:
        """Clear all collected data."""
        self.history.clear()
        self._points.clear()

    def __len__(self) -> int:
        return len(self._points)
