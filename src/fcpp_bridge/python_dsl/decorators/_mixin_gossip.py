from typing import Any, Callable


class _MixinGossip:
    """Gossip-protocol methods for distributed aggregation."""

    def gossip_max(self, value: Any) -> Any:
        """Replicate maximum value across neighbors."""
        from ..primitives import MaxHood
        return MaxHood(value)

    def gossip_sum(self, value: Any) -> Any:
        """Replicate sum across neighbors."""
        from ..primitives import FoldHood
        return FoldHood(0, lambda a, b: a + b)

    def gossip(self, value: Any, accumulate: Callable) -> Any:
        """Gossip a value across the network with a given accumulation function."""
        from ..primitives import Gossip
        return Gossip(value, accumulate)

    def gossip_avg(self, value: Any) -> Any:
        """Replicate average across neighbors."""
        from ..primitives import Gossip
        return Gossip(value, lambda a, b: (a + b) / 2)

    def gossip_count(self) -> int:
        """Count nodes in network."""
        from ..primitives import CountHood
        return CountHood()
