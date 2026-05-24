from typing import Any


class _MixinTime:
    """Temporal aggregate primitives."""

    def constant(self, value: Any) -> Any:
        from ..primitives import Constant
        return Constant(value)

    def constant_after(self, value: Any, t: float) -> Any:
        from ..primitives import ConstantAfter
        return ConstantAfter(value, t)

    def counter(self, start: Any = None, increment: Any = None) -> Any:
        from ..primitives import Counter
        return Counter(start, increment)

    def delay(self, value: Any, n: int) -> Any:
        from ..primitives import Delay
        return Delay(value, n)

    def round_since(self, condition: Any) -> Any:
        from ..primitives import RoundSince
        return RoundSince(condition)

    def time_since(self, condition: Any) -> Any:
        from ..primitives import TimeSince
        return TimeSince(condition)

    def timed_decay(self, value: Any, null: Any, dt: float) -> Any:
        from ..primitives import TimedDecay
        return TimedDecay(value, null, dt)

    def exponential_filter(self, value: Any, factor: float,
                            initial: Any = None) -> Any:
        from ..primitives import ExponentialFilter
        return ExponentialFilter(value, factor, initial)

    def shared_clock(self) -> Any:
        from ..primitives import SharedClock
        return SharedClock()

    def shared_decay(self, value: Any, factor: float,
                     initial: Any = None) -> Any:
        from ..primitives import SharedDecay
        return SharedDecay(value, factor, initial)

    def shared_filter(self, value: Any, factor: float,
                      initial: Any = None) -> Any:
        from ..primitives import SharedFilter
        return SharedFilter(value, factor, initial)

    def toggle(self, change: Any, start: bool = False) -> Any:
        from ..primitives import Toggle
        return Toggle(change, start)

    def toggle_filter(self, change: Any, start: bool = False) -> Any:
        from ..primitives import ToggleFilter
        return ToggleFilter(change, start)
