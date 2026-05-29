"""Shared exercise utilities — position and storage initialisation helpers."""

from fcpp_bridge.exercises.ex_utils.position import (
    Positions,
    grid_in_area,
    rnd_in_area,
)
from fcpp_bridge.exercises.ex_utils.storage import (
    NodeStorage,
    rnd_vec,
    rnd_vec_variable,
    set_rnd_vec,
    set_rnd_vec_variable,
    spread_data_coprime_ID,
    spread_data_coprime_ID_pos,
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
]
