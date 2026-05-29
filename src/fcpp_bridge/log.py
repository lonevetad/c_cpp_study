"""Bridge logging — a thin, toggleable wrapper around Python's ``logging`` module.

By default the bridge emits nothing (a ``NullHandler`` is registered at import
time, which is the recommended practice for library code).  Callers opt in by
calling :func:`configure_bridge_logging`.

Usage inside a bridge sub-module::

    from fcpp_bridge.log import get_logger
    _log = get_logger(__name__)

    _log.debug("Transpiling %s", cls.__name__)
    _log.warning("Lambda default arguments are not supported in C++ output")

Global configuration (done once, typically at application startup)::

    import logging
    from fcpp_bridge.log import configure_bridge_logging
    configure_bridge_logging(level=logging.INFO, stream=sys.stdout)

Toggle on / off without losing handler configuration::

    from fcpp_bridge.log import set_bridge_logging
    set_bridge_logging(False)   # silence all bridge output
    set_bridge_logging(True)    # restore
"""

from __future__ import annotations

import logging
import sys
from typing import IO, Optional


# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

_ROOT_NAME: str = "fcpp_bridge"
_DEFAULT_FMT: str = "[%(levelname)s] %(name)s: %(message)s"
_DEFAULT_TIMED_FMT: str = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"

# Level value that silences all child loggers through effective-level inheritance.
# (Child loggers with no explicit level inherit from root; isEnabledFor returns False.)
_DISABLED_LEVEL: int = logging.CRITICAL + 1

# Level to restore when re-enabling.  Updated by set_bridge_logging(False).
_saved_level: int = logging.DEBUG

# The single root logger for the entire bridge.  Every sub-module acquires a
# child via get_logger(__name__) which delegates to this root.
_root: logging.Logger = logging.getLogger(_ROOT_NAME)
_root.addHandler(logging.NullHandler())   # silent until explicitly configured


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_logger(name: str) -> logging.Logger:
    """Return a child logger scoped under the bridge root (``fcpp_bridge.*``).

    Pass ``__name__`` from the calling module so the logger hierarchy mirrors
    the package hierarchy.
    """
    if name == _ROOT_NAME or name.startswith(f"{_ROOT_NAME}."):
        return logging.getLogger(name)
    return logging.getLogger(f"{_ROOT_NAME}.{name}")


def configure_bridge_logging(
    level: int = logging.DEBUG,
    *,
    stream: Optional[IO] = None,
    filename: Optional[str] = None,
    fmt: str = _DEFAULT_FMT,
    timed: bool = False,
) -> None:
    """Configure the bridge root logger.

    Parameters
    ----------
    level:
        Verbosity level — e.g. ``logging.DEBUG``, ``logging.INFO``.
    stream:
        Output stream.  Defaults to ``sys.stderr``.  Ignored when *filename*
        is given.
    filename:
        Path to a log file.  Opens in append mode with UTF-8 encoding.
        Mutually exclusive with *stream*.
    fmt:
        ``logging.Formatter`` format string.  The default omits timestamps.
    timed:
        If ``True`` and *fmt* is the default, switches to the timestamped
        format (``%(asctime)s …``).  Has no effect when a custom *fmt* is
        passed.
    """
    if timed and fmt == _DEFAULT_FMT:
        fmt = _DEFAULT_TIMED_FMT

    _root.setLevel(level)
    _root.handlers.clear()

    handler: logging.Handler
    if filename is not None:
        handler = logging.FileHandler(filename, encoding="utf-8")
    else:
        handler = logging.StreamHandler(stream if stream is not None else sys.stderr)

    handler.setFormatter(logging.Formatter(fmt))
    _root.addHandler(handler)


def set_bridge_logging(enabled: bool) -> None:
    """Enable or disable all bridge logging without removing handlers.

    Uses level-based silencing so that child loggers (which inherit their
    effective level from the root) are also silenced.  Python's
    ``Logger.disabled`` flag is *not* used because it is only checked in
    ``Logger.handle()``; records propagated from child loggers call
    ``callHandlers()`` directly and bypass that check.

    Calling ``set_bridge_logging(True)`` restores the level that was active
    immediately before the last ``set_bridge_logging(False)`` call.
    """
    global _saved_level
    if enabled:
        _root.setLevel(_saved_level)
    else:
        _saved_level = _root.level if _root.level else logging.DEBUG
        _root.setLevel(_DISABLED_LEVEL)


def is_bridge_logging_enabled() -> bool:
    """Return ``True`` when bridge logging is not silenced."""
    return _root.level < _DISABLED_LEVEL
