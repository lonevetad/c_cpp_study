"""
Position initialization utilities for fcpp_bridge exercise networks.

All functions return a ``Positions`` dict: ``dict[int, tuple[float, ...]]``
mapping node-ID → position.  Node IDs are consecutive integers starting from 0
unless the caller provides its own ID set.

Functions
---------
rnd_in_area(n, area, *, seed=None)
    Place *n* nodes uniformly at random inside a rectangular area (2-D or 3-D).
grid_in_area(n, area, *, row_major=True)
    Place *n* nodes on a regular 2-D grid that covers *area*.
"""

from __future__ import annotations

import math
import random as _random
from typing import Dict, Optional, Tuple

# Public type alias re-exported by ex_utils/__init__.py.
Positions = Dict[int, Tuple[float, ...]]


def rnd_in_area(
    n: int,
    area: Tuple[float, ...],
    *,
    seed: Optional[int] = None,
) -> Positions:
    """Place *n* nodes uniformly at random within a rectangular *area*.

    Parameters
    ----------
    n:
        Number of nodes.  Node IDs are ``0 … n-1``.
    area:
        Bounding box as a flat tuple of even length.  The first half gives the
        lower bound for each dimension and the second half the upper bound:

        - 2-D: ``(xmin, ymin, xmax, ymax)``
        - 3-D: ``(xmin, ymin, zmin, xmax, ymax, zmax)``

        Any even length ≥ 2 is accepted, so 1-D ``(lo, hi)`` also works.
    seed:
        Optional RNG seed for reproducibility.

    Returns
    -------
    Positions
        ``{0: (x0, y0), 1: (x1, y1), …}`` with the same dimensionality as
        ``len(area) // 2``.

    Raises
    ------
    ValueError
        If ``len(area)`` is odd or less than 2, or if any lower bound exceeds
        its corresponding upper bound.

    Examples
    --------
    >>> pos = rnd_in_area(4, (0.0, 0.0, 100.0, 100.0), seed=0)
    >>> len(pos)
    4
    >>> all(0.0 <= x <= 100.0 and 0.0 <= y <= 100.0 for x, y in pos.values())
    True
    """
    if len(area) < 2 or len(area) % 2 != 0:
        raise ValueError(
            f"area must have an even number of elements >= 2; got {len(area)}"
        )
    dim = len(area) // 2
    lo = area[:dim]
    hi = area[dim:]
    for d in range(dim):
        if lo[d] > hi[d]:
            raise ValueError(
                f"area lower bound {lo[d]} exceeds upper bound {hi[d]} "
                f"in dimension {d}"
            )
    rng = _random.Random(seed)
    return {
        i: tuple(rng.uniform(lo[d], hi[d]) for d in range(dim))
        for i in range(n)
    }


def grid_in_area(
    n: int,
    area: Tuple[float, float, float, float],
    *,
    row_major: bool = True,
) -> Positions:
    """Place *n* nodes on a regular 2-D grid that covers *area*.

    The grid has ``ceil(sqrt(n))`` columns and enough rows to seat all *n*
    nodes.  When *n* is not a perfect square, trailing grid cells are skipped
    and only the first *n* IDs (``0 … n-1``) are emitted.

    Parameters
    ----------
    n:
        Number of nodes.
    area:
        Bounding box ``(xmin, ymin, xmax, ymax)``.
    row_major:
        When ``True`` (default) IDs increase left-to-right, then
        top-to-bottom.  When ``False``, top-to-bottom then left-to-right.

    Returns
    -------
    Positions
        ``{0: (x0, y0), …, n-1: (xn, yn)}``.

    Examples
    --------
    >>> pos = grid_in_area(4, (0.0, 0.0, 1.0, 1.0))
    >>> pos[0]
    (0.0, 0.0)
    >>> pos[3]
    (1.0, 1.0)
    """
    xmin, ymin, xmax, ymax = area
    cols = math.ceil(math.sqrt(n))
    rows = math.ceil(n / cols)

    xs = [
        xmin + (xmax - xmin) * c / max(cols - 1, 1)
        for c in range(cols)
    ]
    ys = [
        ymin + (ymax - ymin) * r / max(rows - 1, 1)
        for r in range(rows)
    ]

    positions: Positions = {}
    nid = 0
    outer, inner = (ys, xs) if row_major else (xs, ys)
    for a in outer:
        for b in inner:
            if nid >= n:
                break
            positions[nid] = (b, a) if row_major else (a, b)
            nid += 1

    return positions
