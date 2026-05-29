"""Shared example utilities — position, storage, and tile geometry helpers."""

from fcpp_bridge.examples.ex_utils.position import (
    Positions,
    grid_in_area,
    rnd_in_area,
)
from fcpp_bridge.examples.ex_utils.storage import (
    NodeStorage,
    rnd_vec,
    rnd_vec_variable,
    set_rnd_vec,
    set_rnd_vec_variable,
    spread_data_coprime_ID,
    spread_data_coprime_ID_pos,
)
from fcpp_bridge.examples.ex_utils.tiles import (
    TileCenter,
    Polygon,
    TileMap,
    grid_tile_centers,
    nearest_tile_center,
    compute_tile_shapes,
    clip_rect_to_rect,
    clip_polygon_to_polygon,
)

__all__ = [
    # position
    "Positions",
    "rnd_in_area",
    "grid_in_area",
    # storage
    "NodeStorage",
    "rnd_vec",
    "rnd_vec_variable",
    "set_rnd_vec",
    "set_rnd_vec_variable",
    "spread_data_coprime_ID",
    "spread_data_coprime_ID_pos",
    # tiles
    "TileCenter",
    "Polygon",
    "TileMap",
    "grid_tile_centers",
    "nearest_tile_center",
    "compute_tile_shapes",
    "clip_rect_to_rect",
    "clip_polygon_to_polygon",
]
