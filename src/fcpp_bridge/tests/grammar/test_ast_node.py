"""Tests for AstNode dataclass."""

import pytest
from fcpp_bridge.grammar import AstNode


def test_ast_node_creation():
    node = AstNode(node_type="expr", value=42)
    assert node.node_type == "expr"
    assert node.value == 42
    assert node.children == []


def test_ast_node_with_children():
    child1 = AstNode(node_type="atom", value=1)
    child2 = AstNode(node_type="atom", value=2)
    parent = AstNode(node_type="binop", value="+", children=[child1, child2])
    assert len(parent.children) == 2
    assert parent.children[0].value == 1
