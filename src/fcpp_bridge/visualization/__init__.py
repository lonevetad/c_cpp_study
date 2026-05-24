"""
Visualization plugin — live / replay GUI for FCPP swarm output (Phase 7).

Public API
----------
VisualizerBase      ABC — attach / detach / replay helpers
TextDashboard       Terminal dashboard, no external dependencies
SwarmVisualizer     Matplotlib live visualization (requires matplotlib)
create_visualizer   Factory — picks best available implementation
"""

from typing import IO, Optional

from .visualizer_base import VisualizerBase
from .text_dashboard import TextDashboard
from .swarm_visualizer import SwarmVisualizer


def create_visualizer(
    collector=None,
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


__all__ = [
    "VisualizerBase",
    "TextDashboard",
    "SwarmVisualizer",
    "create_visualizer",
]
