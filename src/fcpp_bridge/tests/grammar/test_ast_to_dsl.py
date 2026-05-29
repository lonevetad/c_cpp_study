"""Tests for ast_to_dsl converter."""

import pytest
from fcpp_bridge.grammar import AstNode, ast_to_dsl


# ============================================================================
# Test 5: AST to DSL conversion
# ============================================================================


def test_ast_to_dsl_int():
    ast = AstNode(node_type="int", value=42)
    dsl = ast_to_dsl(ast)
    assert dsl["type"] == "int"
    assert dsl["value"] == 42


def test_ast_to_dsl_binop():
    left = AstNode(node_type="int", value=1)
    right = AstNode(node_type="int", value=2)
    ast = AstNode(node_type="binop", value="+", children=[left, right])
    dsl = ast_to_dsl(ast)
    assert dsl["type"] == "binop"
    assert dsl["op"] == "+"


# ============================================================================
# Test 8: AST-to-DSL extended
# ============================================================================


def test_ast_to_dsl_float():
    dsl = ast_to_dsl(AstNode(node_type="float", value=3.14))
    assert dsl["type"] == "float"
    assert dsl["value"] == pytest.approx(3.14)


def test_ast_to_dsl_name():
    dsl = ast_to_dsl(AstNode(node_type="name", value="my_var"))
    assert dsl["type"] == "name"
    assert dsl["value"] == "my_var"


def test_ast_to_dsl_call():
    arg = AstNode(node_type="name", value="x")
    ast_node = AstNode(node_type="call", name="nbr", children=[arg])
    dsl = ast_to_dsl(ast_node)
    assert dsl["type"] == "call"
    assert dsl["name"] == "nbr"
    assert dsl["arg"]["value"] == "x"


def test_ast_to_dsl_function():
    initial_state = AstNode(node_type="initial_state", children=[AstNode(node_type="float", value=0.0)])
    compute = AstNode(node_type="compute", children=[AstNode(node_type="name", value="s")])
    func = AstNode(node_type="function", name="avg", children=[initial_state, compute])
    dsl = ast_to_dsl(func)
    assert dsl["type"] == "function"
    assert dsl["name"] == "avg"


def test_ast_to_dsl_program_with_function():
    initial = AstNode(node_type="initial_state", children=[AstNode(node_type="int", value=0)])
    compute = AstNode(node_type="compute", children=[AstNode(node_type="name", value="s")])
    func = AstNode(node_type="function", name="f", children=[initial, compute])
    program = AstNode(node_type="program", children=[func])
    dsl = ast_to_dsl(program)
    assert dsl["type"] == "program"
    assert len(dsl["functions"]) == 1
    assert dsl["functions"][0]["name"] == "f"
