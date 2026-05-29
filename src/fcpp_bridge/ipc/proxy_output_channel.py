from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict

from .output_channel import OutputChannel


class ProxyOutputChannel(OutputChannel):
    """Fan-out output channel that dispatches :meth:`send` to N sub-channels.

    Parameters
    ----------
    mode:
        ``"sequential"`` (default) — calls each sub-channel in registration order.
        ``"parallel"`` — dispatches to all sub-channels concurrently via a thread pool.

    Usage::

        proxy = ProxyOutputChannel()
        proxy.add_channel(LoggingOutputChannel())
        proxy.add_channel(FileOutputChannel("fleet.jsonl"))
        manager = DeviceManager(output_channel=proxy)
    """

    def __init__(self, mode: str = "sequential") -> None:
        if mode not in ("sequential", "parallel"):
            raise ValueError(f"mode must be 'sequential' or 'parallel', got {mode!r}")
        self._mode = mode
        self._channels: Dict[int, OutputChannel] = {}
        self._next_id: int = 0

    def add_channel(self, ch: OutputChannel) -> int:
        """Register a sub-channel and return its integer ID (used to remove it later)."""
        cid = self._next_id
        self._next_id += 1
        self._channels[cid] = ch
        return cid

    def remove_channel(self, channel_id: int) -> None:
        """Unregister a sub-channel by ID.  No-op if the ID does not exist."""
        self._channels.pop(channel_id, None)

    def send(self, name: str, payload: Any) -> None:
        channels = list(self._channels.values())
        if self._mode == "sequential":
            for ch in channels:
                ch.send(name, payload)
        else:
            if not channels:
                return
            with ThreadPoolExecutor(max_workers=len(channels)) as ex:
                list(ex.map(lambda ch: ch.send(name, payload), channels))

    def close(self) -> None:
        for ch in self._channels.values():
            ch.close()
        self._channels.clear()

    def clone(self) -> "ProxyOutputChannel":
        c = ProxyOutputChannel(self._mode)
        for cid, ch in self._channels.items():
            c._channels[cid] = ch.clone()
        c._next_id = self._next_id
        return c
