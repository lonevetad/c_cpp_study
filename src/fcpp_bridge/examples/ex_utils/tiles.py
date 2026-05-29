"""
Tile geometry utilities for fcpp_bridge area-coverage examples.

Provides helpers for generating tile grids over rectangular areas, computing
per-tile polygon shapes, and clipping polygons using Sutherland-Hodgman.

Types
-----
TileCenter  Tuple[float, float]                 — (cx, cy) tile centre
Polygon     List[Tuple[float, float]]           — ordered corners (CCW)
TileMap     Dict[TileCenter, Polygon]           — centre → polygon corners

Functions
---------
grid_tile_centers(area, cell_size)
    Return {tile_id: (cx, cy)} for every tile whose centre lies inside *area*.

nearest_tile_center(pos, tile_centers)
    Return the TileCenter closest to *pos* (Euclidean distance, 2-D).

compute_tile_shapes(tile_centers, area, cell_size)
    Return {(cx, cy): polygon_corners} — border tiles are clipped to *area*.

clip_rect_to_rect(inner, outer_area)
    Sutherland-Hodgman clip of *inner* polygon against a rectangular boundary.

clip_polygon_to_polygon(subject, clip)
    Full Sutherland-Hodgman algorithm for an arbitrary convex *clip* polygon.

Note on polygon convexity (Version B extension)
-------------------------------------------------
The Sutherland-Hodgman algorithm requires a *convex* clip polygon.  The
exercise plan specifies that Version B uses a "non-self-intersecting polygon"
as the deployment area, which may be non-convex.  For non-convex areas,
decompose into convex sub-polygons and union the clipped results.
"""

from __future__ import annotations

import math
from typing import Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Public type aliases
# ---------------------------------------------------------------------------

TileCenter = Tuple[float, float]
Polygon = List[Tuple[float, float]]
TileMap = Dict[TileCenter, Polygon]


# ---------------------------------------------------------------------------
# Grid generation
# ---------------------------------------------------------------------------

def grid_tile_centers(
    area: Tuple[float, float, float, float],
    cell_size: float,
) -> Dict[int, TileCenter]:
    """Return ``{tile_id: (cx, cy)}`` for all tiles whose centres lie inside *area*.

    Tile centres are placed at ``xmin + cell/2``, ``xmin + 3*cell/2``, … along
    both axes.  A small epsilon is used to handle floating-point boundaries.

    Parameters
    ----------
    area:
        ``(xmin, ymin, xmax, ymax)`` bounding box.
    cell_size:
        Side length of each square tile.

    Returns
    -------
    Dict[int, TileCenter]
        Consecutive integer keys starting from 0.

    Examples
    --------
    >>> tiles = grid_tile_centers((0.0, 0.0, 400.0, 400.0), 100.0)
    >>> len(tiles)
    16
    >>> tiles[0]
    (50.0, 50.0)
    """
    eps = 1e-9  # float-boundary tolerance
    if cell_size <= eps:
        raise Exception(
            f"given cell_size must be strictly positive and greater than {eps}: {cell_size}")
    xmin, ymin, xmax, ymax = area
    half = cell_size / 2.0
    centers: Dict[int, TileCenter] = {}
    tid = 0

    cx = xmin + half
    # iterate over all possible "squares" inside this rectangle and extracts all tiles centers in a grid-aligned way
    while cx <= xmax + eps:
        if cx > xmax:
            break
        cy = ymin + half
        while cy <= ymax + eps:
            if cy > ymax:
                break
            centers[tid] = (cx, cy)
            tid += 1
            cy += cell_size
        cx += cell_size

    return centers


def nearest_tile_center(
    pos: Tuple[float, ...],
    tile_centers: Dict[int, TileCenter],
) -> TileCenter:
    """Return the TileCenter from *tile_centers* closest to *pos* (2-D distance).

    Parameters
    ----------
    pos:
        Node position; only the first two components are used.
    tile_centers:
        Output of :func:`grid_tile_centers` or any ``{id: (cx, cy)}`` mapping.

    Raises
    ------
    ValueError
        If *tile_centers* is empty.

    Examples
    --------
    >>> tc = {0: (50.0, 50.0), 1: (150.0, 50.0)}
    >>> nearest_tile_center((60.0, 55.0), tc)
    (50.0, 50.0)
    """
    if not tile_centers:
        raise ValueError("tile_centers must not be empty")
    p = pos[:2]
    return min(tile_centers.values(), key=lambda tc: math.dist(p, tc))


# ---------------------------------------------------------------------------
# Tile shapes
# ---------------------------------------------------------------------------

def compute_tile_shapes(
    tile_centers: Dict[int, TileCenter],
    area: Tuple[float, float, float, float],
    cell_size: float,
) -> TileMap:
    """Return ``{(cx, cy): polygon_corners}`` for every tile in *tile_centers*.

    Interior tiles: axis-aligned square ``(cx ± cell/2, cy ± cell/2)`` in CCW order.
    Border/corner tiles: same square, clipped to *area* with :func:`clip_rect_to_rect`.

    Parameters
    ----------
    tile_centers:
        Output of :func:`grid_tile_centers`.
    area:
        ``(xmin, ymin, xmax, ymax)`` deployment boundary.
    cell_size:
        Tile side length (same value used in :func:`grid_tile_centers`).

    Returns
    -------
    TileMap
        Keys are ``(cx, cy)`` tuples; values are CCW polygon corner lists.
    """
    result: TileMap = {}
    half = cell_size / 2.0

    for center in tile_centers.values():
        cx, cy = center
        # Full square (CCW: bottom-left → bottom-right → top-right → top-left)
        square: Polygon = [
            (cx - half, cy - half),
            (cx + half, cy - half),
            (cx + half, cy + half),
            (cx - half, cy + half),
        ]
        clipped = clip_rect_to_rect(square, area)
        result[center] = clipped if clipped else square

    return result


# ---------------------------------------------------------------------------
# Polygon clipping — Sutherland-Hodgman
# ---------------------------------------------------------------------------

def clip_rect_to_rect(
    inner: Polygon,
    outer_area: Tuple[float, float, float, float],
) -> Polygon:
    """Clip *inner* polygon against a rectangular *outer_area* (Sutherland-Hodgman).

    Delegates to :func:`clip_polygon_to_polygon` with *outer_area* expressed as
    a 4-vertex CCW polygon.

    Parameters
    ----------
    inner:
        Subject polygon (list of (x, y) vertices; any winding order).
    outer_area:
        ``(xmin, ymin, xmax, ymax)`` rectangle used as the clip boundary.

    Returns
    -------
    Polygon
        Clipped polygon (empty list if no intersection).
    """
    xmin, ymin, xmax, ymax = outer_area
    clip_poly: Polygon = [
        (xmin, ymin),
        (xmax, ymin),
        (xmax, ymax),
        (xmin, ymax),
    ]
    return clip_polygon_to_polygon(inner, clip_poly)


def clip_polygon_to_polygon(subject: Polygon, clip: Polygon) -> Polygon:
    """Sutherland-Hodgman algorithm: clip *subject* polygon against convex *clip*.

    Each edge of *clip* defines a half-plane; the algorithm iteratively retains
    the portion of *subject* inside each half-plane.  The clip polygon must be
    convex (CCW winding assumed; CW also works as long as it is consistent).

    Used by ``iteratively_area_discovery`` when the deployment area is a
    non-rectangular convex polygon.  For non-convex areas, decompose into convex
    sub-polygons and union the clipped results.

    Parameters
    ----------
    subject:
        The polygon to clip (list of (x, y) vertices).
    clip:
        Convex clip polygon (list of (x, y) vertices, CCW winding).

    Returns
    -------
    Polygon
        Clipped polygon; empty list if *subject* lies entirely outside *clip*.

    Examples
    --------
    >>> sq = [(0,0),(2,0),(2,2),(0,2)]
    >>> clip_polygon_to_polygon(sq, [(0,0),(1,0),(1,1),(0,1)])
    [(0, 0), (1, 0), (1, 1), (0, 1)]
    """
    if not subject or not clip:
        return []

    output = list(subject)
    n = len(clip)

    for i in range(n):
        if not output:
            return []
        input_list = output
        output = []
        edge_start = clip[i]
        edge_end = clip[(i + 1) % n]

        for j in range(len(input_list)):
            current = input_list[j]
            previous = input_list[j - 1]  # j==0 wraps to last element

            c_inside = _inside(current,  edge_start, edge_end)
            p_inside = _inside(previous, edge_start, edge_end)

            if c_inside:
                if not p_inside:
                    pt = _line_intersection(
                        previous, current, edge_start, edge_end)
                    if pt is not None:
                        output.append(pt)
                output.append(current)
            elif p_inside:
                pt = _line_intersection(
                    previous, current, edge_start, edge_end)
                if pt is not None:
                    output.append(pt)

    return output


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _inside(
    point: Tuple[float, float],
    edge_start: Tuple[float, float],
    edge_end: Tuple[float, float],
) -> bool:
    """Return True if *point* is on or to the left of the directed edge (CCW)."""
    ex = edge_end[0] - edge_start[0]
    ey = edge_end[1] - edge_start[1]
    px = point[0] - edge_start[0]
    py = point[1] - edge_start[1]
    # Cross product z-component: positive → left side (inside for CCW clip polygon)
    return (ex * py - ey * px) >= 0.0


def _line_intersection(
    p1: Tuple[float, float],
    p2: Tuple[float, float],
    p3: Tuple[float, float],
    p4: Tuple[float, float],
) -> Optional[Tuple[float, float]]:
    """Intersection point of line segment p1-p2 with the line through p3-p4.

    Returns ``None`` when the lines are parallel (denominator < ε).
    """
    x1, y1 = p1
    x2, y2 = p2
    x3, y3 = p3
    x4, y4 = p4

    denom = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
    if abs(denom) < 1e-12:
        return None  # parallel

    t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / denom
    return (x1 + t * (x2 - x1), y1 + t * (y2 - y1))
