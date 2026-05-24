"""Tests for CppCodeBuilder — C++ source file assembly."""

import pytest
from fcpp_bridge.transpiler import CppCodeBuilder


# ============================================================================
# Test 1: Code builder basics
# ============================================================================


def test_code_builder_empty():
    builder = CppCodeBuilder()
    code = builder.build()
    assert isinstance(code, str)


def test_code_builder_includes():
    builder = CppCodeBuilder()
    builder.add_include("<vector>")
    builder.add_include("<iostream>")
    code = builder.build()
    assert "#include <vector>" in code
    assert "#include <iostream>" in code


def test_code_builder_declarations():
    builder = CppCodeBuilder()
    builder.add_declaration("struct MyState { double x; int y; };")
    code = builder.build()
    assert "struct MyState" in code


def test_code_builder_no_duplicate_includes():
    builder = CppCodeBuilder()
    builder.add_include("<vector>")
    builder.add_include("<vector>")
    code = builder.build()
    assert code.count("#include <vector>") == 1


# ============================================================================
# Test 8: CppCodeBuilder — helpers and main aggregate
# ============================================================================


def test_code_builder_add_helper():
    b = CppCodeBuilder()
    b.add_helper("int helper() { return 0; }")
    code = b.build()
    assert "int helper()" in code


def test_code_builder_set_main_aggregate():
    b = CppCodeBuilder()
    b.set_main_aggregate("AGGREGATE_TEMPLATE(main) { }")
    code = b.build()
    assert "AGGREGATE_TEMPLATE(main)" in code


def test_code_builder_order():
    b = CppCodeBuilder()
    b.add_include("<vector>")
    b.add_declaration("struct S {};")
    b.add_helper("void f() {}")
    b.set_main_aggregate("void g() {}")
    code = b.build()
    assert code.index("#include") < code.index("struct S") < code.index("void f") < code.index("void g")
