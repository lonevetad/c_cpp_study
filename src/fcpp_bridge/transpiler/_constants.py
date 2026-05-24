"""FCPP primitive → coordination header mapping."""

from typing import Dict

_B = "<lib/coordination/basics.hpp>"
_U = "<lib/coordination/utils.hpp>"
_S = "<lib/coordination/spreading.hpp>"
_C = "<lib/coordination/collection.hpp>"
_G = "<lib/coordination/geometry.hpp>"
_E = "<lib/coordination/election.hpp>"
_T = "<lib/coordination/time.hpp>"

_FCPP_PRIMITIVES: Dict[str, str] = {
    # basics.hpp
    "nbr": _B, "old": _B, "nbr_uid": _B, "oldnbr": _B,
    "align": _B, "align_inplace": _B, "mod_other": _B,
    "fold_hood": _B, "count_hood": _B, "spawn": _B, "split": _B,
    # utils.hpp
    "min_hood": _U, "max_hood": _U, "sum_hood": _U, "mean_hood": _U,
    "all_hood": _U, "any_hood": _U, "list_hood": _U,
    # spreading.hpp
    "broadcast": _S, "abf_distance": _S, "abf_hops": _S,
    "bis_distance": _S, "flex_distance": _S, "bis_ksource_broadcast": _S,
    # collection.hpp
    "gossip": _C, "gossip_min": _C, "gossip_max": _C, "gossip_mean": _C,
    "sp_collection": _C, "mp_collection": _C, "wmp_collection": _C,
    "list_idem_collection": _C, "list_arith_collection": _C,
    # geometry.hpp
    "follow_target": _G, "follow_path": _G, "follow_track": _G,
    "rectangle_walk": _G, "random_rectangle_target": _G,
    "neighbour_elastic_force": _G, "neighbour_gravitational_force": _G,
    "neighbour_charged_force": _G, "line_elastic_force": _G,
    "plane_elastic_force": _G, "point_elastic_force": _G,
    "point_gravitational_force": _G,
    # election.hpp
    "diameter_election": _E, "diameter_election_distance": _E,
    "color_election": _E, "color_election_distance": _E,
    "wave_election": _E, "wave_election_distance": _E,
    # time.hpp
    "constant": _T, "constant_after": _T, "counter": _T, "delay": _T,
    "round_since": _T, "time_since": _T, "timed_decay": _T,
    "exponential_filter": _T, "shared_clock": _T, "shared_decay": _T,
    "shared_filter": _T, "toggle": _T, "toggle_filter": _T,
}
