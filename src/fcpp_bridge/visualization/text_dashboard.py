import sys
from typing import IO, List, Optional

from fcpp_bridge.ipc import SwarmSnapshot

from .visualizer_base import VisualizerBase


class TextDashboard(VisualizerBase):
    """
    Terminal dashboard — one summary line per simulation round.

    No external dependencies. Writes to stdout by default.
    """

    def __init__(self, stream: Optional[IO[str]] = None):
        self._stream = stream if stream is not None else sys.stdout
        self._round_count = 0

    def start(self) -> None:
        print("=== FCPP Swarm Monitor (text) ===", file=self._stream)

    def stop(self) -> None:
        print(f"=== Stopped after {self._round_count} rounds ===", file=self._stream)

    def update(self, snapshot: SwarmSnapshot) -> None:
        self._round_count += 1
        values: List[float] = [
            float(n.state_data)
            for n in snapshot.nodes
            if isinstance(n.state_data, (int, float))
        ]
        if values:
            mean_v = sum(values) / len(values)
            print(
                f"round={snapshot.round_number:>6}  nodes={len(snapshot.nodes):>5}"
                f"  mean={mean_v:>10.4f}"
                f"  min={min(values):>10.4f}"
                f"  max={max(values):>10.4f}",
                file=self._stream,
            )
        else:
            print(
                f"round={snapshot.round_number:>6}  nodes={len(snapshot.nodes):>5}"
                f"  (no numeric state)",
                file=self._stream,
            )
