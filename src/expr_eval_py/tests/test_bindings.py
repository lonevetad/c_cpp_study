"""
Unit tests for the expr_eval_py Python bindings.
Run with:  /c/python314/python.exe -m pytest tests/ -v
           (from the expr_eval_py/ directory)
"""

import pytest
from expr_eval_py import evaluate, version, ParseError, EvaluationError


# ── sanity ────────────────────────────────────────────────────────────────────

def test_version_returns_string():
    v = version()
    assert isinstance(v, str) and len(v) > 0


# ── literals ──────────────────────────────────────────────────────────────────

def test_literal_true():
    assert evaluate("true") is True

def test_literal_false():
    assert evaluate("false") is False


# ── variable lookup ───────────────────────────────────────────────────────────

def test_variable_bool_true():
    assert evaluate("flag", {"flag": "true"}) is True

def test_variable_bool_false():
    assert evaluate("flag", {"flag": "false"}) is False

def test_no_variables_argument():
    # variables defaults to empty — literal expression must still work.
    assert evaluate("true") is True


# ── equality == / != ──────────────────────────────────────────────────────────

def test_eq_number_true():
    assert evaluate("v == 1", {"v": "1"}) is True

def test_eq_number_false():
    assert evaluate("v == 2", {"v": "1"}) is False

def test_neq_number_true():
    assert evaluate("v != 2", {"v": "1"}) is True

def test_neq_number_false():
    assert evaluate("v != 1", {"v": "1"}) is False

def test_eq_bool_true():
    assert evaluate("v == true", {"v": "true"}) is True

def test_eq_bool_false():
    assert evaluate("v == false", {"v": "true"}) is False

def test_hetero_eq_is_false():
    # bool vs number with kAllowHeterogeneousComparisons=true → EQ returns false
    assert evaluate("v == 1", {"v": "true"}) is False

def test_hetero_neq_is_true():
    assert evaluate("v != 1", {"v": "true"}) is True


# ── numeric comparisons ───────────────────────────────────────────────────────

def test_gt_true():
    assert evaluate("v > 10", {"v": "15.5"}) is True

def test_gt_false():
    assert evaluate("v > 20", {"v": "15.5"}) is False

def test_gte_equal():
    assert evaluate("v >= 15.5", {"v": "15.5"}) is True

def test_lt_true():
    assert evaluate("v < 10", {"v": "5"}) is True

def test_lt_false():
    assert evaluate("v < 3", {"v": "5"}) is False

def test_lte_equal():
    assert evaluate("v <= 5", {"v": "5"}) is True

def test_negative_number():
    assert evaluate("v < 0", {"v": "-15"}) is True


# ── logical AND ───────────────────────────────────────────────────────────────

def test_and_tt():
    assert evaluate("a && b", {"a": "true", "b": "true"}) is True

def test_and_tf():
    assert evaluate("a && b", {"a": "true", "b": "false"}) is False

def test_and_ft():
    assert evaluate("a && b", {"a": "false", "b": "true"}) is False

def test_and_ff():
    assert evaluate("a && b", {"a": "false", "b": "false"}) is False

def test_and_short_circuit():
    # false && <unknown> must not throw — RHS never evaluated
    assert evaluate("a && unknown", {"a": "false"}) is False


# ── logical OR ────────────────────────────────────────────────────────────────

def test_or_tt():
    assert evaluate("a || b", {"a": "true", "b": "true"}) is True

def test_or_tf():
    assert evaluate("a || b", {"a": "true", "b": "false"}) is True

def test_or_ft():
    assert evaluate("a || b", {"a": "false", "b": "true"}) is True

def test_or_ff():
    assert evaluate("a || b", {"a": "false", "b": "false"}) is False

def test_or_short_circuit():
    # true || <unknown> must not throw — RHS never evaluated
    assert evaluate("a || unknown", {"a": "true"}) is True


# ── NOT ───────────────────────────────────────────────────────────────────────

def test_not_true():
    assert evaluate("!v", {"v": "true"}) is False

def test_not_false():
    assert evaluate("!v", {"v": "false"}) is True

def test_double_not():
    assert evaluate("!!v", {"v": "true"}) is True
    assert evaluate("!!v", {"v": "false"}) is False


# ── NEGATE ────────────────────────────────────────────────────────────────────

def test_negate():
    assert evaluate("-v > 0", {"v": "-5"}) is True

def test_double_negate_collapses():
    assert evaluate("--v == v", {"v": "7"}) is True


# ── parentheses ───────────────────────────────────────────────────────────────

def test_parens_single():
    assert evaluate("(v == 1)", {"v": "1"}) is True

def test_parens_nested():
    assert evaluate("((v == 1))", {"v": "1"}) is True


# ── complex expressions (from main.cpp) ───────────────────────────────────────

VARS = {"v0": "1", "v1": "15.55", "v2": "5",
        "v3": "-15.000000001", "v4": "true", "v5": "false"}

def test_e1():
    assert evaluate("v0 == 1", VARS) is True

def test_e2():
    assert evaluate("(v0 == 2 || v1 > 10)", VARS) is True

def test_e3():
    assert evaluate("(v0 == 2 || (v1 > 10 && v2 > 3)) && v3 == 0", VARS) is False

def test_e4():
    assert evaluate(
        "(v0 == 2 || (v1 > 10 && v2 > 3)) && v3 == -15.000000001 && !v4", VARS
    ) is False

def test_e5():
    assert evaluate(
        "(v0 == 2 || (v1 > 10 && v2 > 3)) && v3 == -15.000000001 && v4", VARS
    ) is True

def test_e6():
    assert evaluate(
        "((v0 == 2 || (v1 > 10 && v2 > 3)) && v3 == -15.000000001 && v4)"
        " && (v5 == !v4)", VARS
    ) is True

def test_e7():
    assert evaluate("true") is True


# ── ParseError ────────────────────────────────────────────────────────────────

def test_parse_error_empty():
    with pytest.raises(ParseError):
        evaluate("")

def test_parse_error_unclosed_paren():
    with pytest.raises(ParseError):
        evaluate("(v == 1")

def test_parse_error_trailing_operator():
    with pytest.raises(ParseError):
        evaluate("v ==")

def test_parse_error_lone_not():
    with pytest.raises(ParseError):
        evaluate("!")

def test_parse_error_lone_minus():
    with pytest.raises(ParseError):
        evaluate("-")

def test_parse_error_is_valueerror():
    # ParseError must be a subclass of ValueError.
    with pytest.raises(ValueError):
        evaluate("")


# ── EvaluationError ───────────────────────────────────────────────────────────

def test_eval_error_bare_number():
    with pytest.raises(EvaluationError):
        evaluate("5")

def test_eval_error_unknown_variable():
    with pytest.raises(EvaluationError):
        evaluate("nonexistent")

def test_eval_error_bool_gt_bool():
    with pytest.raises(EvaluationError):
        evaluate("true > false")

def test_eval_error_negate_bool():
    with pytest.raises(EvaluationError):
        evaluate("-true")

def test_eval_error_number_and_bool():
    with pytest.raises(EvaluationError):
        evaluate("n && true", {"n": "42"})

def test_eval_error_is_runtimeerror():
    # EvaluationError must be a subclass of RuntimeError.
    with pytest.raises(RuntimeError):
        evaluate("5")


# ── multiple variables ────────────────────────────────────────────────────────

def test_many_variables():
    vars_ = {f"x{i}": str(i) for i in range(20)}
    assert evaluate("x0 < x19", vars_) is True

def test_empty_variables_dict():
    assert evaluate("true", {}) is True
