import copy
from abc import ABC, abstractmethod
from typing import Any


class OutputChannel(ABC):
    """Abstract base for pluggable output channels.

    All concrete channels implement :meth:`send` and optionally :meth:`close`.
    :meth:`clone` provides the Prototype pattern so a channel template can be
    duplicated (e.g. to give each swarm its own file channel).

    Usage::

        ch = FileOutputChannel("fleet.jsonl")
        manager = DeviceManager(output_channel=ch)
    """

    @abstractmethod
    def send(self, name: str, payload: Any) -> None:
        """Emit a named payload to this channel.

        Parameters
        ----------
        name:
            Short identifier for the event source (e.g. ``"start_all"``).
        payload:
            Arbitrary data — a string message, a dict, a snapshot, etc.
        """

    def close(self) -> None:
        """Release any resources held by this channel (file handles, threads, …)."""

    def clone(self) -> "OutputChannel":
        """Return a shallow copy of this channel (Prototype pattern).

        Subclasses that hold mutable state should override this to return a
        proper independent copy.
        """
        return copy.copy(self)
