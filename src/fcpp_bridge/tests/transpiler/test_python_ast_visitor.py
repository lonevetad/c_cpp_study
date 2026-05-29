"""Tests for PythonAstVisitor — all operator, control-flow, and FCPP primitive handling."""

import ast
import inspect
import textwrap
import pytest
from enum import IntEnum
from fcpp_bridge.transpiler import PythonAstVisitor, _FCPP_PRIMITIVES


# Module-level test enum used by constant-folding tests.
class _TestRole(IntEnum):
    UNASSIGNED = 0
    RECEIVER = 1
    SENSOR = 2


def _v(expr_str: str) -> str:
    """Parse expr_str and visit with PythonAstVisitor."""
    v = PythonAstVisitor()
    return v.visit(ast.parse(expr_str).body[0].value)


def _ve(src: str) -> str:
    """Parse src as an eval-mode expression."""
    tree = ast.parse(src, mode="eval")
    return PythonAstVisitor().visit(tree.body)


def _stmt(src: str) -> str:
    """Parse a single statement and return its C++ equivalent."""
    v = PythonAstVisitor()
    return v.visit(ast.parse(src).body[0])


def _body(fn) -> str:
    """Transpile the full body of a zero-argument function to C++."""
    source = textwrap.dedent(inspect.getsource(fn))
    tree = ast.parse(source)
    func_def = tree.body[0]
    stmts = func_def.body
    # skip docstring
    if (
        stmts
        and isinstance(stmts[0], ast.Expr)
        and isinstance(stmts[0].value, ast.Constant)
        and isinstance(stmts[0].value.value, str)
    ):
        stmts = stmts[1:]
    v = PythonAstVisitor()
    return v.transpile_statements(stmts)


def _body_with_consts(fn, constants: dict) -> str:
    """Transpile the full body of fn using a PythonAstVisitor with constants."""
    source = textwrap.dedent(inspect.getsource(fn))
    tree = ast.parse(source)
    func_def = tree.body[0]
    stmts = func_def.body
    if (
        stmts
        and isinstance(stmts[0], ast.Expr)
        and isinstance(stmts[0].value, ast.Constant)
        and isinstance(stmts[0].value.value, str)
    ):
        stmts = stmts[1:]
    v = PythonAstVisitor(constants=constants)
    return v.transpile_statements(stmts)


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


def test_ast_visitor_self_uid():
    """self_uid() → node.uid (no CALL counter)."""
    v = PythonAstVisitor()
    result = v.visit(ast.parse("self_uid()").body[0].value)
    assert result == "node.uid"
    assert "CALL" not in result
    assert "self_uid" not in result


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


# ============================================================================
# Phase 6: expressions — ternary, bool ops, unary, keyword args
# ============================================================================


def test_ternary_expression():
    assert _ve("a if cond else b") == "(cond ? a : b)"


def test_ternary_nested():
    result = _ve("1 if x > 0 else 0")
    assert "?" in result and ":" in result


def test_bool_op_and():
    assert "&&" in _ve("a and b")


def test_bool_op_or():
    assert "||" in _ve("a or b")


def test_bool_op_chain():
    result = _ve("a and b and c")
    assert result.count("&&") == 2


def test_unary_not():
    result = _ve("not x")
    assert "!" in result and "x" in result


def test_unary_neg():
    assert "(-x)" == _ve("-x")


def test_keyword_args_in_call():
    result = _v("MyState(value=v, distance=d)")
    assert "MyState(" in result
    assert "v" in result and "d" in result


def test_list_literal():
    result = _ve("[1, 2, 3]")
    assert "{" in result and "1" in result


def test_method_call_on_object():
    result = _ve("obj.method(x, y)")
    assert "obj.method(x, y)" == result


# ============================================================================
# Phase 6: statements — assign, augassign, return, pass
# ============================================================================


def test_assign_first_use_declares_auto():
    result = _stmt("x = 42")
    assert result == "auto x = 42;"


def test_assign_second_use_no_auto():
    v = PythonAstVisitor()
    v.declared_vars.add("x")
    node = ast.parse("x = 99").body[0]
    assert v.visit(node) == "x = 99;"


def test_augassign_add():
    assert _stmt("x += 1") == "x += 1;"


def test_augassign_sub():
    assert _stmt("x -= 2") == "x -= 2;"


def test_augassign_mul():
    assert _stmt("x *= 3") == "x *= 3;"


def test_return_statement():
    assert _stmt("return x") == "return x;"


def test_return_none():
    assert _stmt("return") == "return;"


def test_pass_statement():
    assert _stmt("pass") == ""


def test_break_statement():
    assert _stmt("break") == "break;"


def test_continue_statement():
    assert _stmt("continue") == "continue;"


# ============================================================================
# Phase 6: if / elif / else
# ============================================================================


def test_if_simple():
    result = _stmt("if x > 0:\n    y = 1")
    assert "if (" in result and "x > 0" in result


def test_if_with_else():
    def fn():
        if x > 0:  # noqa: F821
            y = 1  # noqa: F821
        else:
            y = 0  # noqa: F821
    result = _body(fn)
    assert "if (" in result
    assert "} else {" in result


def test_if_elif_else():
    def fn():
        if a == 1:  # noqa: F821
            x = 10  # noqa: F821
        elif a == 2:  # noqa: F821
            x = 20  # noqa: F821
        else:
            x = 0  # noqa: F821
    result = _body(fn)
    assert "if (" in result
    assert "else if (" in result
    assert "} else {" in result


def test_if_early_return():
    def fn():
        if not values:  # noqa: F821
            return s  # noqa: F821
        return s + 1  # noqa: F821
    result = _body(fn)
    assert "if (" in result
    assert result.count("return") == 2


# ============================================================================
# Phase 6: while loop
# ============================================================================


def test_while_loop():
    def fn():
        while i < 10:  # noqa: F821
            i += 1  # noqa: F821
    result = _body(fn)
    assert "while (" in result
    assert "i < 10" in result
    assert "i += 1" in result


def test_while_with_break():
    def fn():
        while True:  # noqa: F821
            if done:  # noqa: F821
                break
    result = _body(fn)
    assert "while (True)" in result
    assert "break;" in result


# ============================================================================
# Phase 6: for-range loop
# ============================================================================


def test_for_range_one_arg():
    def fn():
        for i in range(10):
            x = i  # noqa: F821
    result = _body(fn)
    assert "for (int i = 0; i < 10; ++i)" in result


def test_for_range_two_args():
    def fn():
        for i in range(2, 8):
            x = i  # noqa: F821
    result = _body(fn)
    assert "for (int i = 2; i < 8; ++i)" in result


def test_for_range_three_args():
    def fn():
        for i in range(0, 20, 2):
            x = i  # noqa: F821
    result = _body(fn)
    assert "for (int i = 0; i < 20; i += 2)" in result


# ============================================================================
# Phase 6: match/case → switch
# ============================================================================


def test_match_case_switch():
    def fn():
        match mode:  # noqa: F821
            case 1:
                x = 10  # noqa: F821
            case 2:
                x = 20  # noqa: F821
            case _:
                x = 0  # noqa: F821
    result = _body(fn)
    assert "switch (" in result
    assert "case 1:" in result
    assert "case 2:" in result
    assert "default:" in result


# ============================================================================
# Phase 6: transpile_statements multi-statement body
# ============================================================================


def test_transpile_full_compute_body():
    def fn():
        is_src = node_id == 0  # noqa: F821
        dist = bis_distance(is_src, 1.0, 100.0)  # noqa: F821
        return dist  # noqa: F821
    result = _body(fn)
    assert "auto is_src" in result
    assert "auto dist" in result
    assert "return dist;" in result


def test_transpile_indentation():
    def fn():
        if x:  # noqa: F821
            return 1
        return 0
    result = _body(fn)
    lines = result.split("\n")
    # outer if is indented 4 spaces
    assert lines[0].startswith("    if (")
    # inner return is indented 8 spaces
    inner = [l for l in lines if "return 1" in l][0]
    assert inner.startswith("        ")


# ============================================================================
# Constant-folding: IntEnum / dotted-attribute chains
# ============================================================================


def test_enum_value_attribute_folds_to_integer():
    """WorkerRole.RECEIVER.value → "1" when constants dict is supplied."""
    v = PythonAstVisitor(constants={"_TestRole": _TestRole})
    node = ast.parse("_TestRole.RECEIVER.value").body[0].value
    assert v.visit(node) == "1"


def test_enum_member_folds_to_integer():
    """IntEnum member without .value also folds (IntEnum IS an int)."""
    v = PythonAstVisitor(constants={"_TestRole": _TestRole})
    node = ast.parse("_TestRole.SENSOR").body[0].value
    assert v.visit(node) == "2"


def test_attribute_no_fold_when_constants_empty():
    """Without a constants dict the dotted chain is emitted verbatim."""
    v = PythonAstVisitor()
    node = ast.parse("_TestRole.RECEIVER.value").body[0].value
    assert v.visit(node) == "_TestRole.RECEIVER.value"


def test_enum_value_in_compare_folds():
    """role == _TestRole.RECEIVER.value → (role == 1)."""
    v = PythonAstVisitor(constants={"_TestRole": _TestRole})
    node = ast.parse("role == _TestRole.RECEIVER.value").body[0].value
    assert v.visit(node) == "(role == 1)"


def test_enum_value_in_match_case_folds():
    """match/case with enum .value patterns emits integer case labels."""
    def fn():
        match mode:  # noqa: F821
            case _TestRole.UNASSIGNED.value:
                x = 0  # noqa: F821
            case _TestRole.RECEIVER.value:
                x = 1  # noqa: F821
            case _:
                x = 99  # noqa: F821
    result = _body_with_consts(fn, {"_TestRole": _TestRole})
    assert "switch (mode)" in result
    assert "case 0:" in result
    assert "case 1:" in result
    assert "default:" in result
    assert "_TestRole" not in result


# ============================================================================
# v2.0: match guard clauses — `case X if cond:` → `case X: if (cond) { ... }`
# ============================================================================


def test_match_guard_simple():
    """case X if cond: → case X: if (cond) { body } break;"""
    def fn():
        match mode:  # noqa: F821
            case 1 if active:  # noqa: F821
                x = 10  # noqa: F821
            case 2:
                x = 20  # noqa: F821
            case _:
                x = 0  # noqa: F821
    result = _body(fn)
    assert "switch (" in result
    assert "case 1:" in result
    assert "if (active)" in result
    assert "case 2:" in result
    assert "default:" in result


def test_match_guard_expression():
    """Guard expressions with comparisons are emitted correctly."""
    def fn():
        match value:  # noqa: F821
            case 0 if dist < threshold:  # noqa: F821
                result = 1  # noqa: F821
            case _:
                result = 0  # noqa: F821
    result = _body(fn)
    assert "case 0:" in result
    assert "if ((dist < threshold))" in result


def test_match_guard_body_indented():
    """Guard body is nested inside the if block."""
    def fn():
        match status:  # noqa: F821
            case 1 if enabled:  # noqa: F821
                y = 42  # noqa: F821
    result = _body(fn)
    # body must appear inside the if block, before the break
    guard_pos = result.index("if (enabled)")
    body_pos = result.index("y = 42", guard_pos)
    break_pos = result.index("break;", guard_pos)
    assert guard_pos < body_pos < break_pos


def test_match_guard_default_with_guard():
    """default: with guard works (wraps body in if block)."""
    def fn():
        match x:  # noqa: F821
            case 1:
                a = 1  # noqa: F821
            case _ if fallback:  # noqa: F821
                a = 0  # noqa: F821
    result = _body(fn)
    assert "default:" in result
    assert "if (fallback)" in result


# ============================================================================
# v2.0: OR patterns — `case A | B:` → `case A: case B:` (C++ fallthrough labels)
# ============================================================================


def test_match_or_pattern_two_values():
    """case A | B: → case A: case B: with shared body."""
    def fn():
        match mode:  # noqa: F821
            case 1 | 2:
                x = 10  # noqa: F821
            case _:
                x = 0  # noqa: F821
    result = _body(fn)
    assert "case 1:" in result
    assert "case 2:" in result
    assert result.count("break;") >= 1


def test_match_or_pattern_three_values():
    """case A | B | C: → three case labels sharing the same body."""
    def fn():
        match role:  # noqa: F821
            case 1 | 2 | 3:
                active = True  # noqa: F821
            case _:
                active = False  # noqa: F821
    result = _body(fn)
    assert "case 1:" in result
    assert "case 2:" in result
    assert "case 3:" in result


def test_match_or_pattern_body_once():
    """The shared body appears only once, not once per label."""
    def fn():
        match mode:  # noqa: F821
            case 0 | 1:
                val = 99  # noqa: F821
    result = _body(fn)
    assert result.count("val = 99") == 1


def test_match_or_pattern_with_enum_folding():
    """OR patterns with enum folding emit integer case labels."""
    def fn():
        match role:  # noqa: F821
            case _TestRole.UNASSIGNED.value | _TestRole.RECEIVER.value:
                ok = True  # noqa: F821
            case _:
                ok = False  # noqa: F821
    result = _body_with_consts(fn, {"_TestRole": _TestRole})
    assert "case 0:" in result
    assert "case 1:" in result
    assert "_TestRole" not in result


# ── Step A — Transpiler completeness (frozenset, min_hood tuple, broadcast) ──


def test_frozenset_with_element():
    """frozenset({self_uid()}) → set_t{node.uid}"""
    result = _v("frozenset({self_uid()})")
    assert result == "set_t{node.uid}"


def test_frozenset_empty():
    """frozenset() → set_t{}"""
    result = _v("frozenset()")
    assert result == "set_t{}"


def test_min_hood_tuple_to_make_tuple():
    """min_hood((x, y)) → min_hood(CALL, std::make_tuple(x, y))"""
    result = _v("min_hood((x, y))")
    assert result == "min_hood(CALL, std::make_tuple(x, y))"


def test_max_hood_tuple_to_make_tuple():
    """max_hood((a, b, c)) → max_hood(CALL, std::make_tuple(a, b, c))"""
    result = _v("max_hood((a, b, c))")
    assert result == "max_hood(CALL, std::make_tuple(a, b, c))"


def test_broadcast_with_self_uid():
    """broadcast(is_receiver, self_uid()) → broadcast(CALL, is_receiver, node.uid)"""
    result = _v("broadcast(is_receiver, self_uid())")
    assert result == "broadcast(CALL, is_receiver, node.uid)"
