"""
Storage (per-node state) initialization utilities for fcpp_bridge examples.

All setter functions operate on a *storage* mapping of the form
``dict[int, dict]`` — node-ID → plain Python dict representing that node's
mutable state.  Each setter writes ``storage[nid][field]`` for every node
currently in *storage*.

The two vector factories (``rnd_vec``, ``rnd_vec_variable``) return a single
``list[float]`` and can be called directly when only one value is needed.
Their in-place counterparts (``set_rnd_vec``, ``set_rnd_vec_variable``) apply
them across the entire node population.

Functions
---------
rnd_vec(length, interval, *, rng=None)
    Return a random vector of *length* floats drawn from *interval*.

rnd_vec_variable(length_range, interval, *, rng=None)
    Return a random vector whose length is drawn from *length_range*.

set_rnd_vec(storage, field, length, interval, *, seed=None)
    Set ``storage[nid][field]`` to an independent fixed-length random vector
    for every node.

set_rnd_vec_variable(storage, field, length_range, interval, *, seed=None)
    Same as ``set_rnd_vec`` but each node's vector length is drawn from
    *length_range*.

spread_data_coprime_ID(storage, positions, comm, field)
    For each node, store the list of coprime-filtered neighbor IDs.

spread_data_coprime_ID_pos(storage, positions, comm, field)
    For each node, store a ``{neighbor_id: neighbor_position}`` map restricted
    to coprime neighbors.  Positions are placeholder values (see note below).
"""

from __future__ import annotations

import math
import random as _random
from math import gcd
from typing import Any, Dict, List, Optional, Tuple

from fcpp_bridge.examples.ex_utils.position import Positions

NodeStorage = Dict[int, Dict[str, Any]]


# ---------------------------------------------------------------------------
# Vector factories
# ---------------------------------------------------------------------------

def rnd_vec(
    length: int,
    interval: Tuple[float, float],
    *,
    rng: Optional[_random.Random] = None,
) -> List[float]:
    """Return a random vector of exactly *length* floats drawn from *interval*.

    Parameters
    ----------
    length:
        Number of elements.  Must be >= 0.
    interval:
        ``(lo, hi)`` inclusive bounds for each element.
    rng:
        Optional :class:`random.Random` instance for reproducibility.
        When ``None``, the module-level RNG is used.

    Returns
    -------
    list[float]

    Examples
    --------
    >>> v = rnd_vec(3, (0.0, 1.0), rng=random.Random(0))
    >>> len(v)
    3
    >>> all(0.0 <= x <= 1.0 for x in v)
    True
    """
    lo, hi = interval
    r: Any = rng if rng is not None else _random
    return [r.uniform(lo, hi) for _ in range(length)]


def rnd_vec_variable(
    length_range: Tuple[int, int],
    interval: Tuple[float, float],
    *,
    rng: Optional[_random.Random] = None,
) -> List[float]:
    """Return a random vector whose length is drawn uniformly from *length_range*.

    Parameters
    ----------
    length_range:
        ``(min_len, max_len)`` inclusive bounds for the vector length.
    interval:
        ``(lo, hi)`` inclusive bounds for each element value.
    rng:
        Optional :class:`random.Random` instance.  Shared between the length
        draw and the element draws so the entire call is reproducible with a
        single seed.

    Returns
    -------
    list[float]

    Examples
    --------
    >>> v = rnd_vec_variable((2, 5), (0.0, 10.0), rng=random.Random(7))
    >>> 2 <= len(v) <= 5
    True
    """
    r: Any = rng if rng is not None else _random
    length = r.randint(*length_range)
    lo, hi = interval
    return [r.uniform(lo, hi) for _ in range(length)]


# ---------------------------------------------------------------------------
# Per-population setters
# ---------------------------------------------------------------------------

def set_rnd_vec(
    storage: NodeStorage,
    field: str,
    length: int,
    interval: Tuple[float, float],
    *,
    seed: Optional[int] = None,
) -> None:
    """Set ``storage[nid][field]`` to an independent random vector for every node.

    Each node receives a distinct vector of exactly *length* floats drawn
    uniformly from *interval*.

    Parameters
    ----------
    storage:
        ``dict[int, dict]`` — node state mapping, modified in place.
    field:
        Key to set in each node's state dict.
    length:
        Fixed vector length (same for all nodes).
    interval:
        ``(lo, hi)`` inclusive bounds for each element.
    seed:
        Optional RNG seed for reproducibility.
    """
    rng = _random.Random(seed)
    for nid in storage:
        storage[nid][field] = rnd_vec(length, interval, rng=rng)


def set_rnd_vec_variable(
    storage: NodeStorage,
    field: str,
    length_range: Tuple[int, int],
    interval: Tuple[float, float],
    *,
    seed: Optional[int] = None,
) -> None:
    """Set ``storage[nid][field]`` to an independent random-length vector for every node.

    Like :func:`set_rnd_vec`, but each node's vector length is drawn
    independently and uniformly from *length_range*.

    Parameters
    ----------
    storage:
        ``dict[int, dict]`` — node state mapping, modified in place.
    field:
        Key to set in each node's state dict.
    length_range:
        ``(min_len, max_len)`` inclusive bounds for the vector length.
    interval:
        ``(lo, hi)`` inclusive bounds for each element value.
    seed:
        Optional RNG seed.
    """
    rng = _random.Random(seed)
    for nid in storage:
        storage[nid][field] = rnd_vec_variable(length_range, interval, rng=rng)


# ---------------------------------------------------------------------------
# Coprime-neighbor setters
# ---------------------------------------------------------------------------

def _coprime_neighbors(
    nid: int,
    positions: Positions,
    comm: float,
) -> List[int]:
    """Return IDs of *nid*'s neighbors that are coprime with *nid*.

    A neighbor *j* qualifies when:
    - ``j != nid``
    - ``math.dist(positions[nid], positions[j]) <= comm``
    - ``gcd(nid, j) == 1``
    """
    p = positions[nid]
    return [
        j for j in positions
        if j != nid
        and math.dist(p, positions[j]) <= comm
        and gcd(nid, j) == 1
    ]


def spread_data_coprime_ID(
    storage: NodeStorage,
    positions: Positions,
    comm: float,
    field: str,
) -> None:
    """For each node, store the list of coprime-filtered neighbor IDs.

    Algorithm (applied per node *nid*)
    ------------------------------------
    1. Find all neighbors of *nid* within *comm* radius.
    2. Retain only those whose ID is coprime with *nid*
       (``gcd(nid, neighbor_id) == 1``).
    3. Write the resulting list to ``storage[nid][field]``.

    Note on node ID 0
    -----------------
    ``gcd(0, j) = j`` for all *j*, so node 0 can only be coprime with node 1
    (where ``gcd(0, 1) = 1``).  All other neighbors of node 0 are filtered out.

    Parameters
    ----------
    storage:
        ``dict[int, dict]`` — node state mapping, modified in place.
    positions:
        ``dict[int, tuple]`` — node positions for neighbor discovery.
        Must contain every node ID that appears in *storage*.
    comm:
        Communication radius (same units as positions).
    field:
        Key to set in each node's state dict.

    Examples
    --------
    >>> storage = {1: {}, 2: {}, 3: {}, 5: {}}
    >>> positions = {1: (0,0), 2: (1,0), 3: (2,0), 5: (3,0)}
    >>> spread_data_coprime_ID(storage, positions, comm=10.0, field='cp_nbrs')
    >>> storage[2]['cp_nbrs']  # gcd(2,1)=1, gcd(2,3)=1 — not 5 (dist>10? no, but gcd(2,5)=1 too)
    [1, 3, 5]
    """
    for nid in storage:
        storage[nid][field] = _coprime_neighbors(nid, positions, comm)


def spread_data_coprime_ID_pos(
    storage: NodeStorage,
    positions: Positions,
    comm: float,
    field: str,
) -> None:
    """For each node, store a ``{neighbor_id: position}`` map for coprime neighbors.

    Identical to :func:`spread_data_coprime_ID` except the stored value is a
    ``dict[int, tuple[float, ...]]`` mapping each coprime-neighbor ID to its
    position, rather than a plain list of IDs.

    The positions are **placeholder values**: they represent the data that a
    real deployment would retrieve from the remote node.  Future exercises
    (e.g. *scattered_database*) replace the position placeholder with actual
    sharded data stored at that neighbor.

    Parameters
    ----------
    storage:
        ``dict[int, dict]`` — node state mapping, modified in place.
    positions:
        ``dict[int, tuple]`` — node positions used both for neighbor
        discovery (via *comm* radius) and as placeholder values in the map.
    comm:
        Communication radius (same units as positions).
    field:
        Key to set in each node's state dict.

    Examples
    --------
    >>> storage = {1: {}, 3: {}}
    >>> positions = {1: (0.0, 0.0), 3: (1.0, 0.0)}
    >>> spread_data_coprime_ID_pos(storage, positions, comm=5.0, field='cp_map')
    >>> storage[1]['cp_map']  # gcd(1, 3) = 1 → included
    {3: (1.0, 0.0)}
    >>> storage[3]['cp_map']  # gcd(3, 1) = 1 → included
    {1: (0.0, 0.0)}
    """
    for nid in storage:
        coprime_nbrs = _coprime_neighbors(nid, positions, comm)
        storage[nid][field] = {j: positions[j] for j in coprime_nbrs}
