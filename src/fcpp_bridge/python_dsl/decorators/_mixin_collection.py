from typing import Any, Callable


class _MixinCollection:
    """Collection methods for distributed data gathering."""

    def sp_collection(self, distance: Any, value: Any, null: Any,
                      accumulate: Callable) -> Any:
        """Single-path collection via tree structure."""
        from ..primitives import SpCollection
        return SpCollection(distance, value, null, accumulate)

    def mp_collection(self, distance: Any, value: Any, null: Any,
                      accumulate: Callable, divide: Callable) -> Any:
        """Multi-path collection via gradient."""
        from ..primitives import MpCollection
        return MpCollection(distance, value, null, accumulate, divide)

    def wmp_collection(self, distance: float, radius: float, value: Any,
                       accumulate: Callable, multiply: Callable) -> Any:
        """Weighted multi-path collection."""
        from ..primitives import WmpCollection
        return WmpCollection(distance, radius, value, accumulate, multiply)
