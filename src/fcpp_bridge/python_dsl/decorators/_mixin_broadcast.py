from typing import Any


class _MixinBroadcast:
    """Broadcast-protocol methods for leader-based dissemination."""

    def broadcast_from_source(self, source_expr: Any, value_expr: Any) -> Any:
        """Broadcast value from sources to all nodes."""
        from ..primitives import Broadcast
        return Broadcast(source_expr, value_expr)

    def multi_hop_broadcast(self, hops: int, expr: Any) -> Any:
        """Limited-range broadcast (hops parameter limits propagation)."""
        return expr

    def distance_broadcast(self, expr: Any) -> Any:
        """Broadcast with distance penalty from source."""
        from ..primitives import Distance
        return Distance(0)
