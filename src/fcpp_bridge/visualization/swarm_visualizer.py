from typing import List

from fcpp_bridge.ipc import SwarmSnapshot

from .visualizer_base import VisualizerBase


class SwarmVisualizer(VisualizerBase):
    """
    Live matplotlib visualization for swarm output.

    Creates a figure with two subplots:
      - Top:    node count per round
      - Bottom: mean value per round with min-max shaded band

    Requires matplotlib.  Raises ``ImportError`` on construction when absent.
    """

    def __init__(
        self,
        title: str = "FCPP Swarm Monitor",
        max_rounds: int = 500,
        update_interval_ms: int = 100,
    ):
        try:
            import matplotlib.pyplot as plt
            import matplotlib.animation as animation
        except ImportError as exc:
            raise ImportError(
                "matplotlib is required for SwarmVisualizer. "
                "Install with: pip install matplotlib"
            ) from exc

        self._plt = plt
        self._animation = animation
        self._title = title
        self._max_rounds = max_rounds
        self._update_interval_ms = update_interval_ms

        self._rounds: List[int] = []
        self._node_counts: List[int] = []
        self._means: List[float] = []
        self._mins: List[float] = []
        self._maxs: List[float] = []

        self._fig = None
        self._ax_nodes = None
        self._ax_values = None
        self._anim = None
        self._dirty = False

    def update(self, snapshot: SwarmSnapshot) -> None:
        """Ingest one new snapshot; marks figure dirty for the next frame."""
        values: List[float] = [
            float(n.state_data)
            for n in snapshot.nodes
            if isinstance(n.state_data, (int, float))
        ]

        self._rounds.append(snapshot.round_number)
        self._node_counts.append(len(snapshot.nodes))

        if values:
            self._means.append(sum(values) / len(values))
            self._mins.append(min(values))
            self._maxs.append(max(values))
        else:
            self._means.append(0.0)
            self._mins.append(0.0)
            self._maxs.append(0.0)

        if len(self._rounds) > self._max_rounds:
            self._rounds = self._rounds[-self._max_rounds:]
            self._node_counts = self._node_counts[-self._max_rounds:]
            self._means = self._means[-self._max_rounds:]
            self._mins = self._mins[-self._max_rounds:]
            self._maxs = self._maxs[-self._max_rounds:]

        self._dirty = True

    def start(self) -> None:
        """Open the visualization window (non-blocking via FuncAnimation)."""
        self._setup_figure()
        self._anim = self._animation.FuncAnimation(
            self._fig,
            self._animate,
            interval=self._update_interval_ms,
            cache_frame_data=False,
        )
        self._plt.show(block=False)

    def stop(self) -> None:
        """Close the visualization window."""
        if self._fig is not None:
            self._plt.close(self._fig)
            self._fig = None

    def replay_from_history(self, collector) -> None:
        """Replay all snapshots from collector's history as a static figure (blocking)."""
        for snapshot in collector.history.to_list():
            self.update(snapshot)
        self._setup_figure()
        self._redraw()
        self._plt.show(block=True)

    def get_data(self) -> dict:
        """Return accumulated data as a plain dict (no display required)."""
        return {
            "rounds": list(self._rounds),
            "node_counts": list(self._node_counts),
            "means": list(self._means),
            "mins": list(self._mins),
            "maxs": list(self._maxs),
        }

    def _setup_figure(self) -> None:
        self._fig, (self._ax_nodes, self._ax_values) = self._plt.subplots(
            2, 1, figsize=(10, 6), tight_layout=True
        )
        self._fig.suptitle(self._title)
        self._ax_nodes.set_xlabel("Round")
        self._ax_nodes.set_ylabel("Node count")
        self._ax_nodes.set_title("Swarm size")
        self._ax_nodes.grid(True, alpha=0.3)
        self._ax_values.set_xlabel("Round")
        self._ax_values.set_ylabel("State value")
        self._ax_values.set_title("Node state statistics (mean ± range)")
        self._ax_values.grid(True, alpha=0.3)

    def _animate(self, _frame: int) -> None:
        if self._dirty:
            self._dirty = False
            self._redraw()

    def _redraw(self) -> None:
        self._ax_nodes.cla()
        self._ax_nodes.set_xlabel("Round")
        self._ax_nodes.set_ylabel("Node count")
        self._ax_nodes.set_title("Swarm size")
        self._ax_nodes.grid(True, alpha=0.3)
        if self._rounds:
            self._ax_nodes.plot(self._rounds, self._node_counts,
                                color="steelblue", linewidth=1.5)

        self._ax_values.cla()
        self._ax_values.set_xlabel("Round")
        self._ax_values.set_ylabel("State value")
        self._ax_values.set_title("Node state statistics (mean ± range)")
        self._ax_values.grid(True, alpha=0.3)
        if self._rounds and self._means:
            self._ax_values.plot(
                self._rounds, self._means, color="darkorange", linewidth=1.5, label="mean"
            )
            self._ax_values.fill_between(
                self._rounds, self._mins, self._maxs,
                alpha=0.2, color="darkorange", label="min-max",
            )
            self._ax_values.legend(loc="upper right", fontsize=8)
