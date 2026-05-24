"""
Visualization plugin — live / replay GUI for FCPP swarm output (Phase 7).

Consumes SwarmSnapshot data via MetricsCollector.on_update() callbacks and
renders it either as a live matplotlib window or as terminal output.

Public API
----------
VisualizerBase      ABC — attach / detach / replay helpers
TextDashboard       Terminal dashboard, no external dependencies
SwarmVisualizer     Matplotlib live visualization (requires matplotlib)
create_visualizer   Factory — picks best available implementation
"""

import sys
from abc import ABC, abstractmethod
from typing import List, Optional, IO

from fcpp_bridge.ipc import NodeState, SwarmSnapshot
from fcpp_bridge.metrics import MetricsCollector


# ============================================================================
# Abstract base
# ============================================================================


class VisualizerBase(ABC):
    """Abstract base for all swarm visualizers."""

    @abstractmethod
    def update(self, snapshot: SwarmSnapshot) -> None:
        """Process one new snapshot. Called by MetricsCollector callbacks."""

    def start(self) -> None:
        """Open/initialise the display. Default: no-op."""

    def stop(self) -> None:
        """Close and clean up the display. Default: no-op."""

    def attach(self, collector: MetricsCollector) -> None:
        """Subscribe self.update to collector.on_update()."""
        collector.on_update(self.update)

    def detach(self, collector: MetricsCollector) -> None:
        """Unsubscribe self.update from collector."""
        collector.remove_callback(self.update)

    def replay_from_history(self, collector: MetricsCollector) -> None:
        """Feed all snapshots from collector's history through update()."""
        for snapshot in collector.history.to_list():
            self.update(snapshot)


# ============================================================================
# Text dashboard
# ============================================================================


class TextDashboard(VisualizerBase):
    """
    Terminal dashboard — one summary line per simulation round.

    No external dependencies. Writes to stdout by default.

    Example output::

        round=     0  nodes=   100  mean=   1.5000  min=   0.0000  max=   3.0000
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


# ============================================================================
# Matplotlib live visualizer
# ============================================================================


class SwarmVisualizer(VisualizerBase):
    """
    Live matplotlib visualization for swarm output.

    Creates a figure with two subplots:
      - Top:    node count per round
      - Bottom: mean value per round with min–max shaded band

    **Live mode** (subscribe to a running swarm)::

        viz = SwarmVisualizer()
        viz.start()           # opens non-blocking window
        viz.attach(collector) # updates window as snapshots arrive

    **Replay mode** (post-hoc, from a populated MetricsCollector)::

        viz = SwarmVisualizer()
        viz.replay_from_history(collector)   # blocking; closes on window close

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

    # ------------------------------------------------------------------
    # VisualizerBase interface
    # ------------------------------------------------------------------

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
            self._rounds = self._rounds[-self._max_rounds :]
            self._node_counts = self._node_counts[-self._max_rounds :]
            self._means = self._means[-self._max_rounds :]
            self._mins = self._mins[-self._max_rounds :]
            self._maxs = self._maxs[-self._max_rounds :]

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

    def replay_from_history(self, collector: MetricsCollector) -> None:
        """
        Replay all snapshots from collector's history as a static figure.

        This is a **blocking** call — the figure stays open until the user
        closes it.
        """
        for snapshot in collector.history.to_list():
            self.update(snapshot)
        self._setup_figure()
        self._redraw()
        self._plt.show(block=True)

    # ------------------------------------------------------------------
    # Data access (useful for testing without a display)
    # ------------------------------------------------------------------

    def get_data(self) -> dict:
        """Return accumulated data as a plain dict (no display required)."""
        return {
            "rounds": list(self._rounds),
            "node_counts": list(self._node_counts),
            "means": list(self._means),
            "mins": list(self._mins),
            "maxs": list(self._maxs),
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

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
        """FuncAnimation tick — redraws only when new data arrived."""
        if self._dirty:
            self._dirty = False
            self._redraw()

    def _redraw(self) -> None:
        """Re-render both subplots from current accumulated data."""
        self._ax_nodes.cla()
        self._ax_nodes.set_xlabel("Round")
        self._ax_nodes.set_ylabel("Node count")
        self._ax_nodes.set_title("Swarm size")
        self._ax_nodes.grid(True, alpha=0.3)
        if self._rounds:
            self._ax_nodes.plot(self._rounds, self._node_counts, color="steelblue", linewidth=1.5)

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
                alpha=0.2, color="darkorange", label="min–max",
            )
            self._ax_values.legend(loc="upper right", fontsize=8)


# ============================================================================
# Factory
# ============================================================================


def create_visualizer(
    collector: Optional[MetricsCollector] = None,
    prefer_gui: bool = True,
    title: str = "FCPP Swarm Monitor",
    max_rounds: int = 500,
    update_interval_ms: int = 100,
    stream: Optional[IO[str]] = None,
) -> VisualizerBase:
    """
    Create the best available visualizer.

    Tries ``SwarmVisualizer`` (matplotlib) first when ``prefer_gui=True``; falls
    back to ``TextDashboard`` if matplotlib is not installed.

    If ``collector`` is provided the visualizer is attached automatically.

    Parameters
    ----------
    collector:
        Optional MetricsCollector to attach to.
    prefer_gui:
        Try matplotlib first (default: True).
    title:
        Window / header title (SwarmVisualizer only).
    max_rounds:
        Maximum rounds to keep in the live chart (SwarmVisualizer only).
    update_interval_ms:
        Animation refresh rate in ms (SwarmVisualizer only).
    stream:
        Output stream (TextDashboard only; default: stdout).
    """
    viz: VisualizerBase
    if prefer_gui:
        try:
            viz = SwarmVisualizer(
                title=title,
                max_rounds=max_rounds,
                update_interval_ms=update_interval_ms,
            )
        except ImportError:
            viz = TextDashboard(stream=stream)
    else:
        viz = TextDashboard(stream=stream)

    if collector is not None:
        viz.attach(collector)

    return viz
