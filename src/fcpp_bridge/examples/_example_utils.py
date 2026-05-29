"""Shared utilities for fcpp_bridge example scripts.

All example ``main()`` functions perform the same boilerplate steps:
  1. Validate the aggregate class and report warnings.
  2. Transpile to C++ and report the generated size.

These helpers centralise that repeated code so each example stays concise.

Shared simulation helpers
--------------------------
``neighbors_of(positions, nid, comm)``
    Returns IDs of all nodes within *comm* radius of *nid* (excluding self).
    Replaces the identical inner function previously defined in every
    ``_demo_simulate()`` body.

``build_positions(n, side_x, side_y, seed)``
    Builds a random 2-D positions dict for *n* nodes.

Spawn status constants
-----------------------
``SPAWN_STATUS_BORDER = 0``   — ``fcpp::status::border``
``SPAWN_STATUS_INTERNAL = 1`` — ``fcpp::status::internal``
``SPAWN_STATUS_TERMINATED = 2`` — ``fcpp::status::terminated_output``
"""

from __future__ import annotations

import logging
import math
import random as _random
from typing import Dict, List, Optional, Tuple, Type

# ---------------------------------------------------------------------------
# Spawn process status codes — mirror fcpp::status enum values exactly.
# These constants are shared by any example that uses the spawn primitive.
# ---------------------------------------------------------------------------

SPAWN_STATUS_BORDER = 0      # fcpp::status::border     (node is off routing path)
SPAWN_STATUS_INTERNAL = 1    # fcpp::status::internal   (node is actively routing)
SPAWN_STATUS_TERMINATED = 2  # fcpp::status::terminated_output (message reached dest)


# ---------------------------------------------------------------------------
# Simulation geometry helpers
# ---------------------------------------------------------------------------

def neighbors_of(
    positions: Dict[int, Tuple[float, ...]],
    nid: int,
    comm: float,
) -> List[int]:
    """Return IDs of all nodes within *comm* radius of *nid*, excluding self.

    *positions* maps node-ID to a position tuple of any dimension (2-D or 3-D).
    Uses ``math.dist`` so it works for both ``(x, y)`` and ``(x, y, z)`` tuples.
    """
    p = positions[nid]
    return [j for j in positions if j != nid and math.dist(p, positions[j]) <= comm]


def build_positions(
    n: int,
    side_x: float,
    side_y: Optional[float] = None,
    *,
    seed: Optional[int] = None,
) -> Dict[int, Tuple[float, float]]:
    """Build a random 2-D positions dict for *n* nodes in ``[0, side_x] × [0, side_y]``.

    Parameters
    ----------
    n:
        Number of nodes.  Keys are ``0 … n-1``.
    side_x:
        Width of the deployment area.
    side_y:
        Height of the deployment area.  Defaults to *side_x* (square area).
    seed:
        Optional RNG seed for reproducibility.
    """
    if side_y is None:
        side_y = side_x
    rng = _random.Random(seed)
    return {i: (rng.uniform(0.0, side_x), rng.uniform(0.0, side_y)) for i in range(n)}


def report_validation(
    cls: Type,
    indent: str = "    ",
    logger: Optional[logging.Logger] = None,
) -> List[str]:
    """Validate *cls*, print/log the result, return the warning list.

    Prints to stdout when *logger* is ``None`` (default); routes through the
    given logger otherwise.  Raises the validator's exception on failure —
    callers should not swallow it.

    Parameters
    ----------
    cls:
        The ``@aggregate_function`` class to validate.
    indent:
        Leading whitespace for status lines.
    logger:
        Optional logger to use instead of ``print``.

    Returns
    -------
    list[str]
        The list of non-fatal warning strings (may be empty).
    """
    from fcpp_bridge.python_dsl.validators import AggregateValidator

    warnings = AggregateValidator.validate(cls)
    ok_msg = f"{indent}OK — {len(warnings)} warning(s)"
    if logger is not None:
        logger.info(ok_msg)
        for w in warnings:
            logger.warning("%s  %s", indent, w)
    else:
        print(ok_msg)
        for w in warnings:
            print(f"{indent}  {w}")
    return warnings


def report_transpilation(
    cls: Type,
    indent: str = "    ",
    logger: Optional[logging.Logger] = None,
) -> Optional[str]:
    """Transpile *cls* to C++, print/log the result, return the C++ string.

    Returns ``None`` on failure (error is printed/logged but not re-raised).

    Parameters
    ----------
    cls:
        The ``@aggregate_function`` class to transpile.
    indent:
        Leading whitespace for status lines.
    logger:
        Optional logger to use instead of ``print``.
    """
    try:
        from fcpp_bridge.transpiler import Transpiler
    except ImportError:
        msg = f"{indent}(transpiler not available in this environment)"
        if logger:
            logger.warning(msg)
        else:
            print(msg)
        return None

    try:
        t = Transpiler(cls)
        cpp = t.generate()
        ok_msg = (
            f"{indent}OK — {len(cpp)} bytes of C++ generated"
            f"  (state type: {t.get_state_type_cpp().name})"
        )
        if logger:
            logger.info(ok_msg)
        else:
            print(ok_msg)
        return cpp
    except Exception as exc:
        err_msg = f"{indent}FAIL: {exc}"
        if logger:
            logger.error(err_msg)
        else:
            print(err_msg)
        return None
