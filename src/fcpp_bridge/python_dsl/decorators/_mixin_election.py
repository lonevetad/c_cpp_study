from typing import Any


class _MixinElection:
    """Leader-election primitives."""

    def diameter_election(self, value: Any, diameter: int) -> Any:
        from ..primitives import DiameterElection
        return DiameterElection(value, diameter)

    def diameter_election_distance(self, value: Any, diameter: int) -> Any:
        from ..primitives import DiameterElectionDistance
        return DiameterElectionDistance(value, diameter)

    def color_election(self, value: Any = None) -> Any:
        from ..primitives import ColorElection
        return ColorElection(value)

    def color_election_distance(self, value: Any = None) -> Any:
        from ..primitives import ColorElectionDistance
        return ColorElectionDistance(value)

    def wave_election(self, value: Any = None, expansion=None) -> Any:
        from ..primitives import WaveElection
        return WaveElection(value, expansion)

    def wave_election_distance(self, value: Any = None, expansion=None) -> Any:
        from ..primitives import WaveElectionDistance
        return WaveElectionDistance(value, expansion)
