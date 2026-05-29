from typing import Any, Callable

from .output_channel import OutputChannel


class CallbackOutputChannel(OutputChannel):
    """Output channel that invokes a ``Callable[[str, Any], None]`` on each send.

    Useful for routing fleet events into custom application logic without
    creating a file or a logger.

    Parameters
    ----------
    fn:
        Called as ``fn(name, payload)`` on every :meth:`send`.
    """

    def __init__(self, fn: Callable[[str, Any], None]) -> None:
        self._fn = fn

    def send(self, name: str, payload: Any) -> None:
        self._fn(name, payload)

    def clone(self) -> "CallbackOutputChannel":
        return CallbackOutputChannel(self._fn)
