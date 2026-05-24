"""Tests for PythonAstVisitor — all operator and FCPP primitive handling."""

import ast
import pytest
from fcpp_bridge.transpiler import PythonAstVisitor, _FCPP_PRIMITIVES


def _v(expr_str: str) -> str:
    """Parse expr_str and visit with PythonAstVisitor."""
    v = PythonAstVisitor()
    return v.visit(ast.parse(expr_str).body[0].value)


def _ve(src: str) -> str:
    """Parse src as an eval-mode expression."""
    tree = ast.parse(src, mode="eval")
    return PythonAstVisitor().visit(tree.body)


# ============================================================================
# Test 3: AST visitor — built-ins and constants
# ============================================================================


def test_ast_visitor_binary_ops():
    v = PythonAstVisitor()
    node = ast.parse("a + b").body[0].value
    result = v.visit(node)
    assert "+" in result and "a" in result and "b" in result

    node = ast.parse("x * y").body[0].value
    result = v.visit(node)
    assert "*" in result


def test_ast_visitor_function_calls():
    v = PythonAstVisitor()
    assert "std::max" in v.visit(ast.parse("max(a, b)").body[0].value)
    assert "std::min" in v.visit(ast.parse("min(x, y)").body[0].value)


def test_ast_visitor_constants():
    v = PythonAstVisitor()
    assert "42" in v.visit(ast.parse("42").body[0].value)
    assert "3.14" in v.visit(ast.parse("3.14").body[0].value)


# ============================================================================
# Test 5: Arithmetic operators
# ============================================================================


def test_ast_visitor_subtraction():
    result = _v("a - b")
    assert "-" in result and "a" in result and "b" in result


def test_ast_visitor_multiplication():
    assert "*" in _v("a * b")


def test_ast_visitor_division():
    assert "/" in _v("x / y")


def test_ast_visitor_modulo():
    assert "%" in _v("x % 3")


def test_ast_visitor_power():
    assert "std::pow" in _v("x ** 2")


# ============================================================================
# Test 6: Comparison operators
# ============================================================================


def test_ast_visitor_less_than():
    assert "<" in _v("a < b")


def test_ast_visitor_greater_than():
    assert ">" in _v("a > b")


def test_ast_visitor_equal():
    assert "==" in _v("a == b")


def test_ast_visitor_not_equal():
    assert "!=" in _v("a != b")


def test_ast_visitor_less_equal():
    assert "<=" in _v("a <= b")


def test_ast_visitor_greater_equal():
    assert ">=" in _v("a >= b")


# ============================================================================
# Test 7: Miscellaneous nodes
# ============================================================================


def test_ast_visitor_string_constant():
    assert '"hello"' in _v('"hello"')


def test_ast_visitor_none_constant():
    assert _v("None") == "nullptr"


def test_ast_visitor_attribute_access():
    assert "obj.attr" in _v("obj.attr")


def test_ast_visitor_subscript():
    assert "arr[0]" in _v("arr[0]")


def test_ast_visitor_len_call():
    assert "size()" in _v("len(arr)")


def test_ast_visitor_sum_call():
    assert "accumulate" in _v("sum(arr)")


def test_ast_visitor_unknown_call():
    assert "custom_fn" in _v("custom_fn(x, y)")


def test_ast_visitor_variable_name():
    v = PythonAstVisitor()
    node = ast.parse("my_var").body[0].value
    assert v.visit(node) == "my_var"


# ============================================================================
# Test 11: FCPP primitives inject CALL
# ============================================================================


def test_ast_visitor_nbr_injects_call():
    assert _v("nbr(x)") == "nbr(CALL, x)"


def test_ast_visitor_old_injects_call():
    assert _v("old(s)") == "old(CALL, s)"


def test_ast_visitor_min_hood_injects_call():
    assert _v("min_hood(x)") == "min_hood(CALL, x)"


def test_ast_visitor_max_hood_injects_call():
    assert _v("max_hood(x)") == "max_hood(CALL, x)"


def test_ast_visitor_count_hood_no_args():
    assert _v("count_hood()") == "count_hood(CALL)"


def test_ast_visitor_fold_hood_two_args():
    assert "fold_hood(CALL," in _v("fold_hood(f, init)")


def test_ast_visitor_broadcast_two_args():
    assert _v("broadcast(dist, val)") == "broadcast(CALL, dist, val)"


def test_ast_visitor_gossip_two_args():
    assert _v("gossip(v, acc)") == "gossip(CALL, v, acc)"


def test_ast_visitor_abf_distance_injects_call():
    assert _v("abf_distance(src)") == "abf_distance(CALL, src)"


def test_ast_visitor_bis_distance_injects_call():
    assert _v("bis_distance(src, p, s)") == "bis_distance(CALL, src, p, s)"


def test_ast_visitor_sp_collection_injects_call():
    assert _v("sp_collection(d, v, n, acc)") == "sp_collection(CALL, d, v, n, acc)"


def test_ast_visitor_mp_collection_injects_call():
    assert _v("mp_collection(d, v, n, acc, div)") == "mp_collection(CALL, d, v, n, acc, div)"


def test_ast_visitor_wmp_collection_injects_call():
    assert _v("wmp_collection(d, r, v, acc, mul)") == "wmp_collection(CALL, d, r, v, acc, mul)"


def test_ast_visitor_rectangle_walk_injects_call():
    assert _v("rectangle_walk(lo, hi, mv, p)") == "rectangle_walk(CALL, lo, hi, mv, p)"


def test_ast_visitor_follow_target_injects_call():
    assert _v("follow_target(tgt, mv, p)") == "follow_target(CALL, tgt, mv, p)"


def test_ast_visitor_spawn_injects_call():
    assert _v("spawn(f, keys)") == "spawn(CALL, f, keys)"


def test_ast_visitor_tracks_used_primitives():
    v = PythonAstVisitor()
    v.visit(ast.parse("nbr(x)").body[0].value)
    v.visit(ast.parse("min_hood(y)").body[0].value)
    assert "nbr" in v.used_primitives
    assert "min_hood" in v.used_primitives


# ============================================================================
# Test 12: New FCPP primitives inject CALL — grouped by header
# ============================================================================


def test_nbr_uid_injects_call():
    assert _v("nbr_uid()") == "nbr_uid(CALL)"


def test_oldnbr_injects_call():
    assert _v("oldnbr(x, op)") == "oldnbr(CALL, x, op)"


def test_align_injects_call():
    assert _v("align(x)") == "align(CALL, x)"


def test_align_inplace_injects_call():
    assert _v("align_inplace(x)") == "align_inplace(CALL, x)"


def test_sum_hood_injects_call():
    assert _v("sum_hood(x)") == "sum_hood(CALL, x)"


def test_mean_hood_injects_call():
    assert _v("mean_hood(x)") == "mean_hood(CALL, x)"


def test_all_hood_injects_call():
    assert _v("all_hood(x)") == "all_hood(CALL, x)"


def test_any_hood_injects_call():
    assert _v("any_hood(x)") == "any_hood(CALL, x)"


def test_list_hood_injects_call():
    assert "list_hood(CALL," in _v("list_hood(c, x)")


def test_abf_hops_injects_call():
    assert _v("abf_hops(s)") == "abf_hops(CALL, s)"


def test_flex_distance_injects_call():
    assert "flex_distance(CALL," in _v("flex_distance(s, e, r, d, f)")


def test_bis_ksource_broadcast_injects_call():
    assert "bis_ksource_broadcast(CALL," in _v("bis_ksource_broadcast(s, v, k, p, sp)")


def test_gossip_min_injects_call():
    assert _v("gossip_min(v)") == "gossip_min(CALL, v)"


def test_gossip_max_injects_call():
    assert _v("gossip_max(v)") == "gossip_max(CALL, v)"


def test_gossip_mean_injects_call():
    assert _v("gossip_mean(v)") == "gossip_mean(CALL, v)"


def test_list_idem_collection_injects_call():
    assert "list_idem_collection(CALL," in _v("list_idem_collection(d, v, r, s, n, e, a)")


def test_list_arith_collection_injects_call():
    assert "list_arith_collection(CALL," in _v("list_arith_collection(d, v, r, s, n, e, a)")


def test_follow_path_injects_call():
    assert "follow_path(CALL," in _v("follow_path(p, v, t)")


def test_follow_track_injects_call():
    assert _v("follow_track(t)") == "follow_track(CALL, t)"


def test_random_rectangle_target_injects_call():
    assert "random_rectangle_target(CALL," in _v("random_rectangle_target(lo, hi)")


def test_neighbour_elastic_force_injects_call():
    assert "neighbour_elastic_force(CALL," in _v("neighbour_elastic_force(l, s)")


def test_diameter_election_injects_call():
    assert "diameter_election(CALL," in _v("diameter_election(v, d)")


def test_color_election_injects_call():
    assert _v("color_election(v)") == "color_election(CALL, v)"


def test_wave_election_injects_call():
    assert _v("wave_election(v)") == "wave_election(CALL, v)"


def test_constant_injects_call():
    assert _v("constant(v)") == "constant(CALL, v)"


def test_counter_no_args_injects_call():
    assert _v("counter()") == "counter(CALL)"


def test_delay_injects_call():
    assert "delay(CALL," in _v("delay(v, n)")


def test_toggle_injects_call():
    assert "toggle(CALL," in _v("toggle(c)")


def test_shared_clock_injects_call():
    assert _v("shared_clock()") == "shared_clock(CALL)"


def test_timed_decay_injects_call():
    assert "timed_decay(CALL," in _v("timed_decay(v, n, dt)")


# ============================================================================
# Test 13: Primitive header mapping correctness
# ============================================================================


def test_all_basics_map_to_correct_header():
    for name in ("nbr", "old", "nbr_uid", "oldnbr", "align", "fold_hood", "count_hood", "spawn"):
        assert "<lib/coordination/basics.hpp>" in _FCPP_PRIMITIVES[name], name


def test_all_utils_map_to_correct_header():
    for name in ("min_hood", "max_hood", "sum_hood", "mean_hood", "all_hood", "any_hood", "list_hood"):
        assert "<lib/coordination/utils.hpp>" in _FCPP_PRIMITIVES[name], name


def test_all_spreading_map_to_correct_header():
    for name in ("broadcast", "abf_distance", "abf_hops", "bis_distance", "flex_distance", "bis_ksource_broadcast"):
        assert "<lib/coordination/spreading.hpp>" in _FCPP_PRIMITIVES[name], name


def test_all_collection_map_to_correct_header():
    for name in ("gossip", "gossip_min", "gossip_max", "gossip_mean",
                 "sp_collection", "mp_collection", "wmp_collection",
                 "list_idem_collection", "list_arith_collection"):
        assert "<lib/coordination/collection.hpp>" in _FCPP_PRIMITIVES[name], name


def test_all_geometry_map_to_correct_header():
    for name in ("follow_target", "follow_path", "rectangle_walk",
                 "neighbour_elastic_force", "point_elastic_force"):
        assert "<lib/coordination/geometry.hpp>" in _FCPP_PRIMITIVES[name], name


def test_all_election_map_to_correct_header():
    for name in ("diameter_election", "color_election", "wave_election",
                 "diameter_election_distance", "color_election_distance", "wave_election_distance"):
        assert "<lib/coordination/election.hpp>" in _FCPP_PRIMITIVES[name], name


def test_all_time_map_to_correct_header():
    for name in ("constant", "counter", "delay", "toggle", "shared_clock",
                 "timed_decay", "exponential_filter", "round_since", "time_since"):
        assert "<lib/coordination/time.hpp>" in _FCPP_PRIMITIVES[name], name


def test_fcpp_primitives_total_count():
    assert len(_FCPP_PRIMITIVES) == 64


# ============================================================================
# v0.9: visit_Lambda — G&& callable support
# ============================================================================


def test_visit_lambda_no_args():
    assert _ve("lambda: 42") == "[=]() { return 42; }"


def test_visit_lambda_one_arg():
    assert _ve("lambda x: x + 1") == "[=](auto x) { return (x + 1); }"


def test_visit_lambda_two_args():
    assert _ve("lambda a, b: a + b") == "[=](auto a, auto b) { return (a + b); }"


def test_visit_lambda_nested_expression():
    cpp = _ve("lambda a, b: a * b + 1")
    assert "[=](auto a, auto b)" in cpp
    assert "return" in cpp


def test_visit_lambda_comparison():
    cpp = _ve("lambda a, b: a < b")
    assert "[=](auto a, auto b)" in cpp
    assert "a < b" in cpp


def test_fcpp_call_with_lambda_arg_fold_hood():
    src = "fold_hood(0, lambda a, b: a + b)"
    assert _ve(src) == "fold_hood(CALL, 0, [=](auto a, auto b) { return (a + b); })"


def test_fcpp_call_with_lambda_arg_gossip():
    src = "gossip(val, lambda a, b: a + b)"
    assert _ve(src) == "gossip(CALL, val, [=](auto a, auto b) { return (a + b); })"


def test_fcpp_call_with_lambda_arg_split():
    src = "split(key, lambda x: x * 2)"
    assert _ve(src) == "split(CALL, key, [=](auto x) { return (x * 2); })"
