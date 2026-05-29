import json
from typing import Any

from fcpp_bridge.log import get_logger
from .output_channel import OutputChannel


class LoggingOutputChannel(OutputChannel):
    """Output channel that emits payloads through the bridge logging system.

    Parameters
    ----------
    level:
        Python logging level name (``"INFO"``, ``"WARNING"``, ``"DEBUG"``, …).
    logger_name:
        Logger name; defaults to ``"fcpp_bridge.output"``.
    """

    def __init__(
        self,
        level: str = "INFO",
        logger_name: str = "fcpp_bridge.output",
    ) -> None:
        self._logger = get_logger(logger_name)
        self._level = level.upper()

    def send(self, name: str, payload: Any) -> None:
        body = payload if isinstance(payload, str) else json.dumps(payload)
        msg = f"[{name}] {body}"
        log_fn = getattr(self._logger, self._level.lower(), self._logger.info)
        log_fn(msg)

    def clone(self) -> "LoggingOutputChannel":
        c = LoggingOutputChannel.__new__(LoggingOutputChannel)
        c._logger = self._logger
        c._level = self._level
        return c
