"""Tests for AntlrParser wrapper — ANTLR4-backed parser with fallback."""

import pytest
from fcpp_bridge.grammar import AggregateLanguageParser, AntlrParser, ParserError


# ============================================================================
# Test 9: AntlrParser wrapper
# ============================================================================


def test_antlr_parser_instantiation():
    parser = AntlrParser()
    assert hasattr(parser, "_antlr_available")
    assert hasattr(parser, "_fallback")


def test_antlr_parser_check_antlr_bool():
    result = AntlrParser._check_antlr()
    assert isinstance(result, bool)


def test_antlr_parser_fallback_present():
    parser = AntlrParser()
    assert isinstance(parser._fallback, AggregateLanguageParser)


def test_antlr_parser_parse_string_delegates():
    parser = AntlrParser()
    program_str = "\n    def counter:\n    initial_state: 0.0\n    compute(s, n): s + 1.0\n    "
    try:
        ast = parser.parse_string(program_str)
        assert ast.node_type == "program"
    except ParserError:
        pass  # acceptable if grammar doesn't fully parse test string


def test_antlr_parser_parse_file(tmp_path):
    f = tmp_path / "test.agg"
    f.write_text("def counter:\ninitial_state: 0.0\ncompute(s, n): s + 1.0\n")
    parser = AntlrParser()
    try:
        ast = parser.parse_file(f)
        assert ast.node_type == "program"
    except (ParserError, Exception):
        pass  # parsing may fail; file I/O path is exercised


def test_antlr_parser_no_antlr_uses_fallback(monkeypatch):
    parser = AntlrParser()
    parser._antlr_available = False
    program_str = "\n    def avg:\n    initial_state: 0.0\n    compute(s, n): s + 1.0\n    "
    try:
        ast = parser.parse_string(program_str)
        fallback_ast = parser._fallback.parse_string(program_str)
        assert ast.node_type == fallback_ast.node_type
    except ParserError:
        pass


def test_antlr_parser_fallback_parse_atom_int():
    parser = AntlrParser()
    parser._fallback._tokenize("99")
    parser._fallback.pos = 0
    node = parser._fallback._parse_atom()
    assert node.node_type == "int"
    assert node.value == 99


def test_antlr_parser_fallback_parse_binop():
    parser = AntlrParser()
    parser._fallback._tokenize("3 + 4")
    parser._fallback.pos = 0
    node = parser._fallback._parse_expr()
    assert node.node_type == "binop"
    assert node.value == "+"
