from abc import ABC, abstractmethod

from fcpp_bridge.ipc import SwarmSnapshot


class VisualizerBase(ABC):
    """Abstract base for all swarm visualizers."""

    @abstractmethod
    def update(self, snapshot: SwarmSnapshot) -> None:
        """Process one new snapshot. Called by MetricsCollector callbacks."""

    def start(self) -> None:
        """Open/initialise the display. Default: no-op."""

    def stop(self) -> None:
        """Close and clean up the display. Default: no-op."""

    def attach(self, collector) -> None:
        """Subscribe self.update to collector.on_update()."""
        collector.on_update(self.update)

    def detach(self, collector) -> None:
        """Unsubscribe self.update from collector."""
        collector.remove_callback(self.update)

    def replay_from_history(self, collector) -> None:
        """Feed all snapshots from collector's history through update()."""
        for snapshot in collector.history.to_list():
            self.update(snapshot)
