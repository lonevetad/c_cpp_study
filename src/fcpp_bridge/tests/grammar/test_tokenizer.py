"""Tests for AggregateLanguageParser tokenizer."""

import pytest
from fcpp_bridge.grammar import AggregateLanguageParser


# ============================================================================
# Test 1: Tokenizer basics
# ============================================================================


def test_parser_tokenize_simple():
    parser = AggregateLanguageParser()
    parser._tokenize("def foo: x = 1")
    assert "def" in parser.tokens
    assert "foo" in parser.tokens
    assert "x" in parser.tokens
    assert "1" in parser.tokens


def test_parser_tokenize_skip_comments():
    parser = AggregateLanguageParser()
    parser._tokenize("x = 1  # comment here")
    assert "#" not in parser.tokens
    assert "comment" not in parser.tokens


def test_parser_tokenize_primitives():
    parser = AggregateLanguageParser()
    parser._tokenize("nbr(x) + max_hood(y)")
    assert "nbr" in parser.tokens
    assert "max_hood" in parser.tokens


def test_parser_parse_numbers():
    parser = AggregateLanguageParser()
    parser._tokenize("42 3.14 0")
    assert parser.tokens == ["42", "3.14", "0"]


def test_parser_parse_names():
    parser = AggregateLanguageParser()
    parser._tokenize("variable_name another_var x")
    assert "variable_name" in parser.tokens
    assert "another_var" in parser.tokens


# ============================================================================
# Test 7: Additional tokenizer coverage
# ============================================================================


def test_parser_tokenize_keywords():
    parser = AggregateLanguageParser()
    parser._tokenize("def initial_state compute if return")
    for kw in ("def", "initial_state", "compute", "if", "return"):
        assert kw in parser.tokens


def test_parser_tokenize_operators():
    parser = AggregateLanguageParser()
    parser._tokenize("x + y - z * w / v")
    for op in ("+", "-", "*", "/"):
        assert op in parser.tokens


def test_parser_tokenize_all_primitives():
    parser = AggregateLanguageParser()
    parser._tokenize("nbr(x) old(y) max_hood(z) min_hood(a) fold_hood(b) count_hood(c)")
    for prim in ("nbr", "old", "max_hood", "min_hood", "fold_hood", "count_hood"):
        assert prim in parser.tokens, f"{prim} not tokenized"


# ============================================================================
# Test 10: New primitive tokenization
# ============================================================================


def test_parser_tokenize_spreading_primitives():
    parser = AggregateLanguageParser()
    parser._tokenize("broadcast(d, v) bis_distance(s, p, sp) abf_distance(s)")
    for prim in ("broadcast", "bis_distance", "abf_distance"):
        assert prim in parser.tokens, f"{prim} not tokenized"


def test_parser_tokenize_collection_primitives():
    parser = AggregateLanguageParser()
    parser._tokenize("gossip(v, acc) sp_collection(d, v, n, acc) mp_collection(d, v, n, acc, div)")
    for prim in ("gossip", "sp_collection", "mp_collection"):
        assert prim in parser.tokens, f"{prim} not tokenized"


def test_parser_tokenize_wmp_collection():
    parser = AggregateLanguageParser()
    parser._tokenize("wmp_collection(d, r, v, acc, mul)")
    assert "wmp_collection" in parser.tokens


def test_parser_tokenize_geometry_primitives():
    parser = AggregateLanguageParser()
    parser._tokenize("rectangle_walk(lo, hi, mv, p) follow_target(tgt, mv, p)")
    assert "rectangle_walk" in parser.tokens
    assert "follow_target" in parser.tokens


def test_parser_tokenize_spawn():
    parser = AggregateLanguageParser()
    parser._tokenize("spawn(f, keys)")
    assert "spawn" in parser.tokens


# ============================================================================
# Test 12: New primitive tokenization — full set
# ============================================================================


def test_parser_tokenize_basics_additions():
    parser = AggregateLanguageParser()
    parser._tokenize("nbr_uid() oldnbr(x, op) align(x) align_inplace(x) mod_other(x) split(k, f)")
    for name in ("nbr_uid", "oldnbr", "align", "align_inplace", "mod_other", "split"):
        assert name in parser.tokens, f"{name} not tokenized"


def test_parser_tokenize_utils_additions():
    parser = AggregateLanguageParser()
    parser._tokenize("sum_hood(x) mean_hood(x) all_hood(x) any_hood(x) list_hood(c, x)")
    for name in ("sum_hood", "mean_hood", "all_hood", "any_hood", "list_hood"):
        assert name in parser.tokens, f"{name} not tokenized"


def test_parser_tokenize_spreading_additions():
    parser = AggregateLanguageParser()
    parser._tokenize("abf_hops(s) flex_distance(s,e,r,d,f) bis_ksource_broadcast(s,v,k,p,sp)")
    for name in ("abf_hops", "flex_distance", "bis_ksource_broadcast"):
        assert name in parser.tokens, f"{name} not tokenized"


def test_parser_tokenize_collection_additions():
    parser = AggregateLanguageParser()
    parser._tokenize("gossip_min(v) gossip_max(v) gossip_mean(v) list_idem_collection(d,v,r,sp,n,e,a) list_arith_collection(d,v,r,sp,n,e,a)")
    for name in ("gossip_min", "gossip_max", "gossip_mean", "list_idem_collection", "list_arith_collection"):
        assert name in parser.tokens, f"{name} not tokenized"


def test_parser_tokenize_geometry_additions():
    parser = AggregateLanguageParser()
    parser._tokenize("follow_path(p,v,t) follow_track(t) random_rectangle_target(lo,hi)")
    for name in ("follow_path", "follow_track", "random_rectangle_target"):
        assert name in parser.tokens, f"{name} not tokenized"


def test_parser_tokenize_physics_forces():
    parser = AggregateLanguageParser()
    parser._tokenize("neighbour_elastic_force(l,s) neighbour_gravitational_force(m) neighbour_charged_force(m,c)")
    for name in ("neighbour_elastic_force", "neighbour_gravitational_force", "neighbour_charged_force"):
        assert name in parser.tokens, f"{name} not tokenized"


def test_parser_tokenize_election():
    parser = AggregateLanguageParser()
    parser._tokenize("diameter_election(v,d) color_election(v) wave_election(v)")
    for name in ("diameter_election", "color_election", "wave_election"):
        assert name in parser.tokens, f"{name} not tokenized"


def test_parser_tokenize_time_primitives():
    parser = AggregateLanguageParser()
    parser._tokenize("constant(v) counter() delay(v,n) toggle(c) shared_clock() timed_decay(v,n,t) exponential_filter(v,f)")
    for name in ("constant", "counter", "delay", "toggle", "shared_clock", "timed_decay", "exponential_filter"):
        assert name in parser.tokens, f"{name} not tokenized"
