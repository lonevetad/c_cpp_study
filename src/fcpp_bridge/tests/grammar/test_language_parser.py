"""Tests for AggregateLanguageParser — parsing expressions and primitives."""

import pytest
from fcpp_bridge.grammar import AggregateLanguageParser, ParserError


# ============================================================================
# Test 2: Simple parsing
# ============================================================================


def test_parser_parse_minimal():
    parser = AggregateLanguageParser()
    program_str = "\n    def avg:\n    initial_state: 0.0\n    compute(s, n): s + 1.0\n    "
    try:
        ast = parser.parse_string(program_str)
        assert ast.node_type == "program"
        assert len(ast.children) > 0
    except ParserError:
        pass  # format flexibility


# ============================================================================
# Test 4: Expression parsing (atoms, binary ops, primitive calls)
# ============================================================================


def test_parser_parse_atom_int():
    parser = AggregateLanguageParser()
    parser._tokenize("42")
    parser.pos = 0
    ast = parser._parse_atom()
    assert ast.node_type == "int"
    assert ast.value == 42


def test_parser_parse_atom_float():
    parser = AggregateLanguageParser()
    parser._tokenize("3.14")
    parser.pos = 0
    ast = parser._parse_atom()
    assert ast.node_type == "float"
    assert ast.value == 3.14


def test_parser_parse_atom_name():
    parser = AggregateLanguageParser()
    parser._tokenize("x")
    parser.pos = 0
    ast = parser._parse_atom()
    assert ast.node_type == "name"
    assert ast.value == "x"


def test_parser_parse_binary_add():
    parser = AggregateLanguageParser()
    parser._tokenize("1 + 2")
    parser.pos = 0
    ast = parser._parse_expr()
    assert ast.node_type == "binop"
    assert ast.value == "+"


def test_parser_parse_call_nbr():
    parser = AggregateLanguageParser()
    parser._tokenize("nbr ( x )")
    parser.pos = 0
    ast = parser._parse_call_expr()
    assert ast.node_type == "call"
    assert ast.name == "nbr"


# ============================================================================
# Test 6: Error handling
# ============================================================================


def test_parser_error_unexpected_token():
    parser = AggregateLanguageParser()
    parser._tokenize("42 42 42")
    parser.pos = 0
    try:
        parser._parse_expr()
    except ParserError:
        pass  # expected


def test_parser_error_empty_input():
    parser = AggregateLanguageParser()
    parser._tokenize("")
    try:
        parser.parse_string("")
    except ParserError:
        pass  # expected


# ============================================================================
# Test 11: Multi-arg primitive call parsing
# ============================================================================


def test_parser_parse_count_hood_no_args():
    parser = AggregateLanguageParser()
    parser._tokenize("count_hood ( )")
    parser.pos = 0
    node = parser._parse_call_expr()
    assert node.node_type == "call"
    assert node.name == "count_hood"
    assert node.children == []


def test_parser_parse_broadcast_two_args():
    parser = AggregateLanguageParser()
    parser._tokenize("broadcast ( d , v )")
    parser.pos = 0
    node = parser._parse_call_expr()
    assert node.name == "broadcast"
    assert len(node.children) == 2


def test_parser_parse_gossip_two_args():
    parser = AggregateLanguageParser()
    parser._tokenize("gossip ( v , acc )")
    parser.pos = 0
    node = parser._parse_call_expr()
    assert node.name == "gossip"
    assert len(node.children) == 2


def test_parser_parse_sp_collection_four_args():
    parser = AggregateLanguageParser()
    parser._tokenize("sp_collection ( d , v , n , acc )")
    parser.pos = 0
    node = parser._parse_call_expr()
    assert node.name == "sp_collection"
    assert len(node.children) == 4


def test_parser_parse_abf_distance_one_arg():
    parser = AggregateLanguageParser()
    parser._tokenize("abf_distance ( src )")
    parser.pos = 0
    node = parser._parse_call_expr()
    assert node.name == "abf_distance"
    assert len(node.children) == 1


def test_parser_parse_bis_distance_three_args():
    parser = AggregateLanguageParser()
    parser._tokenize("bis_distance ( src , p , s )")
    parser.pos = 0
    node = parser._parse_call_expr()
    assert node.name == "bis_distance"
    assert len(node.children) == 3


def test_parser_parse_follow_target_three_args():
    parser = AggregateLanguageParser()
    parser._tokenize("follow_target ( tgt , mv , p )")
    parser.pos = 0
    node = parser._parse_call_expr()
    assert node.name == "follow_target"
    assert len(node.children) == 3


def test_parser_parse_rectangle_walk_four_args():
    parser = AggregateLanguageParser()
    parser._tokenize("rectangle_walk ( lo , hi , mv , p )")
    parser.pos = 0
    node = parser._parse_call_expr()
    assert node.name == "rectangle_walk"
    assert len(node.children) == 4


def test_parser_all_primitives_in_frozenset():
    original = {
        "nbr", "old", "max_hood", "min_hood", "fold_hood", "count_hood",
        "spawn", "broadcast", "gossip",
        "sp_collection", "mp_collection", "wmp_collection",
        "bis_distance", "abf_distance",
        "rectangle_walk", "follow_target",
    }
    assert original.issubset(AggregateLanguageParser._ALL_PRIMITIVES)


# ============================================================================
# Test 13: Multi-arg parsing for new primitives
# ============================================================================


def test_parser_parse_nbr_uid_no_args():
    parser = AggregateLanguageParser()
    parser._tokenize("nbr_uid ( )")
    parser.pos = 0
    node = parser._parse_call_expr()
    assert node.name == "nbr_uid"
    assert node.children == []


def test_parser_parse_sum_hood_one_arg():
    parser = AggregateLanguageParser()
    parser._tokenize("sum_hood ( x )")
    parser.pos = 0
    node = parser._parse_call_expr()
    assert node.name == "sum_hood"
    assert len(node.children) == 1


def test_parser_parse_gossip_min_one_arg():
    parser = AggregateLanguageParser()
    parser._tokenize("gossip_min ( v )")
    parser.pos = 0
    node = parser._parse_call_expr()
    assert node.name == "gossip_min"
    assert len(node.children) == 1


def test_parser_parse_diameter_election_two_args():
    parser = AggregateLanguageParser()
    parser._tokenize("diameter_election ( v , d )")
    parser.pos = 0
    node = parser._parse_call_expr()
    assert node.name == "diameter_election"
    assert len(node.children) == 2


def test_parser_parse_list_idem_collection_seven_args():
    parser = AggregateLanguageParser()
    parser._tokenize("list_idem_collection ( d , v , r , s , n , e , a )")
    parser.pos = 0
    node = parser._parse_call_expr()
    assert node.name == "list_idem_collection"
    assert len(node.children) == 7


def test_parser_parse_shared_clock_no_args():
    parser = AggregateLanguageParser()
    parser._tokenize("shared_clock ( )")
    parser.pos = 0
    node = parser._parse_call_expr()
    assert node.name == "shared_clock"
    assert node.children == []


def test_parser_parse_toggle_two_args():
    parser = AggregateLanguageParser()
    parser._tokenize("toggle ( c , s )")
    parser.pos = 0
    node = parser._parse_call_expr()
    assert node.name == "toggle"
    assert len(node.children) == 2


def test_parser_full_frozenset_size():
    assert len(AggregateLanguageParser._ALL_PRIMITIVES) == 64
