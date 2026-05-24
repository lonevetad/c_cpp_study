"""Tests for Phase 2 Transpiler."""

import pytest
from fcpp_bridge.python_dsl import aggregate_function, Neighborhood
from fcpp_bridge.transpiler import Transpiler, CppCodeBuilder, TranspilationError


# ============================================================================
# Test 1: Code builder
# ============================================================================


def test_code_builder_empty():
    """Test empty code builder."""
    builder = CppCodeBuilder()
    code = builder.build()
    assert isinstance(code, str)


def test_code_builder_includes():
    """Test adding includes."""
    builder = CppCodeBuilder()
    builder.add_include("<vector>")
    builder.add_include("<iostream>")
    code = builder.build()
    assert "#include <vector>" in code
    assert "#include <iostream>" in code


def test_code_builder_declarations():
    """Test adding type declarations."""
    builder = CppCodeBuilder()
    builder.add_declaration("struct MyState { double x; int y; };")
    code = builder.build()
    assert "struct MyState" in code


def test_code_builder_no_duplicate_includes():
    """Test that duplicate includes are not added."""
    builder = CppCodeBuilder()
    builder.add_include("<vector>")
    builder.add_include("<vector>")
    code = builder.build()
    assert code.count("#include <vector>") == 1


# ============================================================================
# Test 2: Basic transpilation
# ============================================================================


def test_transpiler_simple_float():
    """Test transpiling simple float aggregate."""

    @aggregate_function
    class SimpleFloat:
        def initial_state(self) -> float:
            return 0.0

        def compute(self, self_state: float, neighbors: Neighborhood[float]) -> float:
            return self_state + 1.0

    transpiler = Transpiler(SimpleFloat)
    cpp_code = transpiler.generate()

    assert isinstance(cpp_code, str)
    assert len(cpp_code) > 0
    assert "#include <fcpp/fcpp.hpp>" in cpp_code
    assert "AGGREGATE_TEMPLATE(main)" in cpp_code


def test_transpiler_int_state():
    """Test transpiling int aggregate."""

    @aggregate_function
    class IntAggregate:
        def initial_state(self) -> int:
            return 0

        def compute(self, self_state: int, neighbors: Neighborhood[int]) -> int:
            return self_state

    transpiler = Transpiler(IntAggregate)
    cpp_code = transpiler.generate()

    assert "int" in cpp_code


def test_transpiler_custom_struct():
    """Test transpiling custom struct aggregate."""
    from dataclasses import dataclass

    @dataclass
    class CustomState:
        x: float
        y: int

    @aggregate_function
    class StructAggregate:
        def initial_state(self) -> CustomState:
            return CustomState(0.0, 0)

        def compute(
            self,
            self_state: CustomState,
            neighbors: Neighborhood[CustomState]
        ) -> CustomState:
            return self_state

    transpiler = Transpiler(StructAggregate)
    cpp_code = transpiler.generate()

    assert "struct CustomState" in cpp_code
    assert "double x" in cpp_code
    assert "int y" in cpp_code


# ============================================================================
# Test 3: AST visitor
# ============================================================================


def test_ast_visitor_binary_ops():
    """Test AST visitor with binary operations."""
    from fcpp_bridge.transpiler import PythonAstVisitor
    import ast

    visitor = PythonAstVisitor()

    # Test addition
    node = ast.parse("a + b").body[0].value
    result = visitor.visit(node)
    assert "+" in result
    assert "a" in result
    assert "b" in result

    # Test multiplication
    node = ast.parse("x * y").body[0].value
    result = visitor.visit(node)
    assert "*" in result


def test_ast_visitor_function_calls():
    """Test AST visitor with function calls."""
    from fcpp_bridge.transpiler import PythonAstVisitor
    import ast

    visitor = PythonAstVisitor()

    # Test max
    node = ast.parse("max(a, b)").body[0].value
    result = visitor.visit(node)
    assert "std::max" in result

    # Test min
    node = ast.parse("min(x, y)").body[0].value
    result = visitor.visit(node)
    assert "std::min" in result


def test_ast_visitor_constants():
    """Test AST visitor with constants."""
    from fcpp_bridge.transpiler import PythonAstVisitor
    import ast

    visitor = PythonAstVisitor()

    # Test number
    node = ast.parse("42").body[0].value
    result = visitor.visit(node)
    assert "42" in result

    # Test float
    node = ast.parse("3.14").body[0].value
    result = visitor.visit(node)
    assert "3.14" in result


# ============================================================================
# Test 4: Code generation
# ============================================================================


def test_transpiler_code_structure():
    """Test that generated code has expected structure."""

    @aggregate_function
    class TestAggregate:
        def initial_state(self) -> float:
            return 1.5

        def compute(self, self_state: float, neighbors: Neighborhood[float]) -> float:
            return self_state

    transpiler = Transpiler(TestAggregate)
    cpp_code = transpiler.generate()

    # Check structure
    assert cpp_code.count("#include") > 0
    assert "AGGREGATE_TEMPLATE" in cpp_code
    assert "compute_next_state" in cpp_code


def test_transpiler_preserves_state_type():
    """Test that transpiler preserves state type info."""

    @aggregate_function
    class TypedAggregate:
        def initial_state(self) -> float:
            return 0.0

        def compute(self, self_state: float, neighbors: Neighborhood[float]) -> float:
            return self_state

    transpiler = Transpiler(TypedAggregate)
    state_cpp_type = transpiler.get_state_type_cpp()

    assert state_cpp_type.name == "double"
    assert state_cpp_type.is_primitive


# ============================================================================
# Test 5: PythonAstVisitor — operators
# ============================================================================


def test_ast_visitor_subtraction():
    from fcpp_bridge.transpiler import PythonAstVisitor
    import ast as _ast
    v = PythonAstVisitor()
    node = _ast.parse("a - b").body[0].value
    result = v.visit(node)
    assert "-" in result and "a" in result and "b" in result


def test_ast_visitor_multiplication():
    from fcpp_bridge.transpiler import PythonAstVisitor
    import ast as _ast
    v = PythonAstVisitor()
    node = _ast.parse("a * b").body[0].value
    result = v.visit(node)
    assert "*" in result


def test_ast_visitor_division():
    from fcpp_bridge.transpiler import PythonAstVisitor
    import ast as _ast
    v = PythonAstVisitor()
    node = _ast.parse("x / y").body[0].value
    result = v.visit(node)
    assert "/" in result


def test_ast_visitor_modulo():
    from fcpp_bridge.transpiler import PythonAstVisitor
    import ast as _ast
    v = PythonAstVisitor()
    node = _ast.parse("x % 3").body[0].value
    result = v.visit(node)
    assert "%" in result


def test_ast_visitor_power():
    from fcpp_bridge.transpiler import PythonAstVisitor
    import ast as _ast
    v = PythonAstVisitor()
    node = _ast.parse("x ** 2").body[0].value
    result = v.visit(node)
    assert "std::pow" in result


# ============================================================================
# Test 6: PythonAstVisitor — comparisons
# ============================================================================


def test_ast_visitor_less_than():
    from fcpp_bridge.transpiler import PythonAstVisitor
    import ast as _ast
    v = PythonAstVisitor()
    node = _ast.parse("a < b").body[0].value
    result = v.visit(node)
    assert "<" in result


def test_ast_visitor_greater_than():
    from fcpp_bridge.transpiler import PythonAstVisitor
    import ast as _ast
    v = PythonAstVisitor()
    node = _ast.parse("a > b").body[0].value
    result = v.visit(node)
    assert ">" in result


def test_ast_visitor_equal():
    from fcpp_bridge.transpiler import PythonAstVisitor
    import ast as _ast
    v = PythonAstVisitor()
    node = _ast.parse("a == b").body[0].value
    result = v.visit(node)
    assert "==" in result


def test_ast_visitor_not_equal():
    from fcpp_bridge.transpiler import PythonAstVisitor
    import ast as _ast
    v = PythonAstVisitor()
    node = _ast.parse("a != b").body[0].value
    result = v.visit(node)
    assert "!=" in result


def test_ast_visitor_less_equal():
    from fcpp_bridge.transpiler import PythonAstVisitor
    import ast as _ast
    v = PythonAstVisitor()
    node = _ast.parse("a <= b").body[0].value
    result = v.visit(node)
    assert "<=" in result


def test_ast_visitor_greater_equal():
    from fcpp_bridge.transpiler import PythonAstVisitor
    import ast as _ast
    v = PythonAstVisitor()
    node = _ast.parse("a >= b").body[0].value
    result = v.visit(node)
    assert ">=" in result


# ============================================================================
# Test 7: PythonAstVisitor — misc nodes
# ============================================================================


def test_ast_visitor_string_constant():
    from fcpp_bridge.transpiler import PythonAstVisitor
    import ast as _ast
    v = PythonAstVisitor()
    node = _ast.parse('"hello"').body[0].value
    result = v.visit(node)
    assert '"hello"' in result


def test_ast_visitor_none_constant():
    from fcpp_bridge.transpiler import PythonAstVisitor
    import ast as _ast
    v = PythonAstVisitor()
    node = _ast.parse("None").body[0].value
    result = v.visit(node)
    assert result == "nullptr"


def test_ast_visitor_attribute_access():
    from fcpp_bridge.transpiler import PythonAstVisitor
    import ast as _ast
    v = PythonAstVisitor()
    node = _ast.parse("obj.attr").body[0].value
    result = v.visit(node)
    assert "obj.attr" in result


def test_ast_visitor_subscript():
    from fcpp_bridge.transpiler import PythonAstVisitor
    import ast as _ast
    v = PythonAstVisitor()
    node = _ast.parse("arr[0]").body[0].value
    result = v.visit(node)
    assert "arr[0]" in result


def test_ast_visitor_len_call():
    from fcpp_bridge.transpiler import PythonAstVisitor
    import ast as _ast
    v = PythonAstVisitor()
    node = _ast.parse("len(arr)").body[0].value
    result = v.visit(node)
    assert "size()" in result


def test_ast_visitor_sum_call():
    from fcpp_bridge.transpiler import PythonAstVisitor
    import ast as _ast
    v = PythonAstVisitor()
    node = _ast.parse("sum(arr)").body[0].value
    result = v.visit(node)
    assert "accumulate" in result


def test_ast_visitor_unknown_call():
    from fcpp_bridge.transpiler import PythonAstVisitor
    import ast as _ast
    v = PythonAstVisitor()
    node = _ast.parse("custom_fn(x, y)").body[0].value
    result = v.visit(node)
    assert "custom_fn" in result


def test_ast_visitor_variable_name():
    from fcpp_bridge.transpiler import PythonAstVisitor
    import ast as _ast
    v = PythonAstVisitor()
    node = _ast.parse("my_var").body[0].value
    assert v.visit(node) == "my_var"


# ============================================================================
# Test 8: CppCodeBuilder — helpers and main aggregate
# ============================================================================


def test_code_builder_add_helper():
    from fcpp_bridge.transpiler import CppCodeBuilder
    b = CppCodeBuilder()
    b.add_helper("int helper() { return 0; }")
    code = b.build()
    assert "int helper()" in code


def test_code_builder_set_main_aggregate():
    from fcpp_bridge.transpiler import CppCodeBuilder
    b = CppCodeBuilder()
    b.set_main_aggregate("AGGREGATE_TEMPLATE(main) { }")
    code = b.build()
    assert "AGGREGATE_TEMPLATE(main)" in code


def test_code_builder_order():
    from fcpp_bridge.transpiler import CppCodeBuilder
    b = CppCodeBuilder()
    b.add_include("<vector>")
    b.add_declaration("struct S {};")
    b.add_helper("void f() {}")
    b.set_main_aggregate("void g() {}")
    code = b.build()
    assert code.index("#include") < code.index("struct S") < code.index("void f") < code.index("void g")


# ============================================================================
# Test 9: AggregateType inference
# ============================================================================


def test_aggregate_type_infer_float():
    from fcpp_bridge.python_dsl import AggregateType
    t = AggregateType.infer(float)
    assert t.name == "double"
    assert t.is_primitive


def test_aggregate_type_infer_int():
    from fcpp_bridge.python_dsl import AggregateType
    t = AggregateType.infer(int)
    assert t.name == "int"
    assert t.is_primitive


def test_aggregate_type_infer_bool():
    from fcpp_bridge.python_dsl import AggregateType
    t = AggregateType.infer(bool)
    assert t.name == "bool"
    assert t.is_primitive


def test_aggregate_type_infer_str():
    from fcpp_bridge.python_dsl import AggregateType
    t = AggregateType.infer(str)
    assert t.name == "std::string"


def test_aggregate_type_infer_list_float():
    from fcpp_bridge.python_dsl import AggregateType
    t = AggregateType.infer(list[float])
    assert "std::vector" in t.name
    assert "double" in t.name


def test_aggregate_type_infer_list_int():
    from fcpp_bridge.python_dsl import AggregateType
    t = AggregateType.infer(list[int])
    assert "std::vector<int>" == t.name


def test_aggregate_type_infer_tuple():
    from fcpp_bridge.python_dsl import AggregateType
    t = AggregateType.infer(tuple[float, int])
    assert "std::tuple" in t.name
    assert "double" in t.name
    assert "int" in t.name


def test_aggregate_type_infer_dict():
    from fcpp_bridge.python_dsl import AggregateType
    t = AggregateType.infer(dict[str, float])
    assert "std::map" in t.name


def test_aggregate_type_infer_dataclass():
    from dataclasses import dataclass
    from fcpp_bridge.python_dsl import AggregateType

    @dataclass
    class Vec2:
        x: float
        y: float

    t = AggregateType.infer(Vec2)
    assert t.name == "Vec2"
    assert t.is_struct
    assert "x" in t.fields
    assert "y" in t.fields


def test_aggregate_type_is_numeric():
    from fcpp_bridge.python_dsl import AggregateType, CppType
    assert AggregateType.is_numeric(CppType("double"))
    assert AggregateType.is_numeric(CppType("int"))
    assert not AggregateType.is_numeric(CppType("std::string"))


def test_aggregate_type_is_container():
    from fcpp_bridge.python_dsl import AggregateType, CppType
    assert AggregateType.is_container(CppType("std::vector<int>"))
    assert AggregateType.is_container(CppType("std::map<int, int>"))
    assert not AggregateType.is_container(CppType("double"))


def test_cpp_type_declaration_primitive():
    from fcpp_bridge.python_dsl import CppType
    t = CppType("double", is_primitive=True)
    assert t.cpp_declaration() == ""


def test_cpp_type_declaration_struct():
    from fcpp_bridge.python_dsl import CppType
    fields = {"x": CppType("double"), "n": CppType("int")}
    t = CppType("MyState", is_struct=True, is_primitive=False, fields=fields)
    decl = t.cpp_declaration()
    assert "struct MyState" in decl
    assert "double x" in decl
    assert "int n" in decl


# ============================================================================
# Test 10: Transpiler with various state types
# ============================================================================


def test_transpiler_bool_state():
    @aggregate_function
    class BoolAggregate:
        def initial_state(self) -> bool:
            return False

        def compute(self, self_state: bool, neighbors: Neighborhood[bool]) -> bool:
            return self_state

    transpiler = Transpiler(BoolAggregate)
    cpp = transpiler.generate()
    assert "bool" in cpp


def test_transpiler_str_state():
    @aggregate_function
    class StrAggregate:
        def initial_state(self) -> str:
            return ""

        def compute(self, self_state: str, neighbors: Neighborhood[str]) -> str:
            return self_state

    transpiler = Transpiler(StrAggregate)
    cpp = transpiler.generate()
    assert "std::string" in cpp


def test_transpiler_list_state():
    @aggregate_function
    class ListAggregate:
        def initial_state(self) -> list[float]:
            return []

        def compute(self, self_state: list[float], neighbors: Neighborhood[list[float]]) -> list[float]:
            return self_state

    transpiler = Transpiler(ListAggregate)
    cpp = transpiler.generate()
    assert "std::vector" in cpp


def test_transpiler_includes_fcpp():
    @aggregate_function
    class FloatAgg:
        def initial_state(self) -> float:
            return 0.0

        def compute(self, self_state: float, neighbors: Neighborhood[float]) -> float:
            return self_state

    cpp = Transpiler(FloatAgg).generate()
    assert cpp.startswith("#include")


def test_transpiler_generate_returns_string():
    @aggregate_function
    class FloatAgg2:
        def initial_state(self) -> float:
            return 1.0

        def compute(self, self_state: float, neighbors: Neighborhood[float]) -> float:
            return self_state

    assert isinstance(Transpiler(FloatAgg2).generate(), str)


def test_transpiler_state_type_int():
    @aggregate_function
    class IntAgg2:
        def initial_state(self) -> int:
            return 42

        def compute(self, self_state: int, neighbors: Neighborhood[int]) -> int:
            return self_state

    t = Transpiler(IntAgg2)
    assert t.get_state_type_cpp().name == "int"


def test_transpiler_state_type_bool():
    @aggregate_function
    class BoolAgg2:
        def initial_state(self) -> bool:
            return True

        def compute(self, self_state: bool, neighbors: Neighborhood[bool]) -> bool:
            return self_state

    t = Transpiler(BoolAgg2)
    assert t.get_state_type_cpp().name == "bool"


def test_transpiler_custom_struct_field_types():
    from dataclasses import dataclass

    @dataclass
    class Pos:
        x: float
        y: float
        count: int

    @aggregate_function
    class PosAggregate:
        def initial_state(self) -> Pos:
            return Pos(0.0, 0.0, 0)

        def compute(self, self_state: Pos, neighbors: Neighborhood[Pos]) -> Pos:
            return self_state

    cpp = Transpiler(PosAggregate).generate()
    assert "struct Pos" in cpp
    assert "double x" in cpp
    assert "double y" in cpp
    assert "int count" in cpp


# ============================================================================
# Test 11: PythonAstVisitor — FCPP primitive calls inject CALL
# ============================================================================


def test_ast_visitor_nbr_injects_call():
    from fcpp_bridge.transpiler import PythonAstVisitor
    import ast as _ast
    v = PythonAstVisitor()
    node = _ast.parse("nbr(x)").body[0].value
    result = v.visit(node)
    assert result == "nbr(CALL, x)"


def test_ast_visitor_old_injects_call():
    from fcpp_bridge.transpiler import PythonAstVisitor
    import ast as _ast
    v = PythonAstVisitor()
    node = _ast.parse("old(s)").body[0].value
    result = v.visit(node)
    assert result == "old(CALL, s)"


def test_ast_visitor_min_hood_injects_call():
    from fcpp_bridge.transpiler import PythonAstVisitor
    import ast as _ast
    v = PythonAstVisitor()
    node = _ast.parse("min_hood(x)").body[0].value
    result = v.visit(node)
    assert result == "min_hood(CALL, x)"


def test_ast_visitor_max_hood_injects_call():
    from fcpp_bridge.transpiler import PythonAstVisitor
    import ast as _ast
    v = PythonAstVisitor()
    node = _ast.parse("max_hood(x)").body[0].value
    result = v.visit(node)
    assert result == "max_hood(CALL, x)"


def test_ast_visitor_count_hood_no_args():
    from fcpp_bridge.transpiler import PythonAstVisitor
    import ast as _ast
    v = PythonAstVisitor()
    node = _ast.parse("count_hood()").body[0].value
    result = v.visit(node)
    assert result == "count_hood(CALL)"


def test_ast_visitor_fold_hood_two_args():
    from fcpp_bridge.transpiler import PythonAstVisitor
    import ast as _ast
    v = PythonAstVisitor()
    node = _ast.parse("fold_hood(f, init)").body[0].value
    result = v.visit(node)
    assert "fold_hood(CALL," in result


def test_ast_visitor_broadcast_two_args():
    from fcpp_bridge.transpiler import PythonAstVisitor
    import ast as _ast
    v = PythonAstVisitor()
    node = _ast.parse("broadcast(dist, val)").body[0].value
    result = v.visit(node)
    assert result == "broadcast(CALL, dist, val)"


def test_ast_visitor_gossip_two_args():
    from fcpp_bridge.transpiler import PythonAstVisitor
    import ast as _ast
    v = PythonAstVisitor()
    node = _ast.parse("gossip(v, acc)").body[0].value
    result = v.visit(node)
    assert result == "gossip(CALL, v, acc)"


def test_ast_visitor_abf_distance_injects_call():
    from fcpp_bridge.transpiler import PythonAstVisitor
    import ast as _ast
    v = PythonAstVisitor()
    node = _ast.parse("abf_distance(src)").body[0].value
    result = v.visit(node)
    assert result == "abf_distance(CALL, src)"


def test_ast_visitor_bis_distance_injects_call():
    from fcpp_bridge.transpiler import PythonAstVisitor
    import ast as _ast
    v = PythonAstVisitor()
    node = _ast.parse("bis_distance(src, p, s)").body[0].value
    result = v.visit(node)
    assert result == "bis_distance(CALL, src, p, s)"


def test_ast_visitor_sp_collection_injects_call():
    from fcpp_bridge.transpiler import PythonAstVisitor
    import ast as _ast
    v = PythonAstVisitor()
    node = _ast.parse("sp_collection(d, v, n, acc)").body[0].value
    result = v.visit(node)
    assert result == "sp_collection(CALL, d, v, n, acc)"


def test_ast_visitor_mp_collection_injects_call():
    from fcpp_bridge.transpiler import PythonAstVisitor
    import ast as _ast
    v = PythonAstVisitor()
    node = _ast.parse("mp_collection(d, v, n, acc, div)").body[0].value
    result = v.visit(node)
    assert result == "mp_collection(CALL, d, v, n, acc, div)"


def test_ast_visitor_wmp_collection_injects_call():
    from fcpp_bridge.transpiler import PythonAstVisitor
    import ast as _ast
    v = PythonAstVisitor()
    node = _ast.parse("wmp_collection(d, r, v, acc, mul)").body[0].value
    result = v.visit(node)
    assert result == "wmp_collection(CALL, d, r, v, acc, mul)"


def test_ast_visitor_rectangle_walk_injects_call():
    from fcpp_bridge.transpiler import PythonAstVisitor
    import ast as _ast
    v = PythonAstVisitor()
    node = _ast.parse("rectangle_walk(lo, hi, mv, p)").body[0].value
    result = v.visit(node)
    assert result == "rectangle_walk(CALL, lo, hi, mv, p)"


def test_ast_visitor_follow_target_injects_call():
    from fcpp_bridge.transpiler import PythonAstVisitor
    import ast as _ast
    v = PythonAstVisitor()
    node = _ast.parse("follow_target(tgt, mv, p)").body[0].value
    result = v.visit(node)
    assert result == "follow_target(CALL, tgt, mv, p)"


def test_ast_visitor_spawn_injects_call():
    from fcpp_bridge.transpiler import PythonAstVisitor
    import ast as _ast
    v = PythonAstVisitor()
    node = _ast.parse("spawn(f, keys)").body[0].value
    result = v.visit(node)
    assert result == "spawn(CALL, f, keys)"


def test_ast_visitor_tracks_used_primitives():
    from fcpp_bridge.transpiler import PythonAstVisitor
    import ast as _ast
    v = PythonAstVisitor()
    v.visit(_ast.parse("nbr(x)").body[0].value)
    v.visit(_ast.parse("min_hood(y)").body[0].value)
    assert "nbr" in v.used_primitives
    assert "min_hood" in v.used_primitives


def test_transpiler_adds_header_for_used_primitive():
    @aggregate_function
    class MinHoodAgg:
        def initial_state(self) -> float:
            return 0.0
        def compute(self, self_state: float, neighbors: Neighborhood[float]) -> float:
            return min_hood(self_state)  # noqa: F821 — transpiler sees name

    cpp = Transpiler(MinHoodAgg).generate()
    assert "<lib/coordination/utils.hpp>" in cpp


def test_transpiler_adds_geometry_header_for_rectangle_walk():
    @aggregate_function
    class WalkAgg:
        def initial_state(self) -> float:
            return 0.0
        def compute(self, self_state: float, neighbors: Neighborhood[float]) -> float:
            return rectangle_walk(lo, hi, 1.0, 0.1)  # noqa: F821

    cpp = Transpiler(WalkAgg).generate()
    assert "<lib/coordination/geometry.hpp>" in cpp


# ============================================================================
# Test 12: New FCPP primitives inject CALL — grouped by header
# ============================================================================


def _visit(expr_str: str) -> str:
    from fcpp_bridge.transpiler import PythonAstVisitor
    import ast as _ast
    v = PythonAstVisitor()
    return v.visit(_ast.parse(expr_str).body[0].value)


def test_nbr_uid_injects_call():
    assert _visit("nbr_uid()") == "nbr_uid(CALL)"


def test_oldnbr_injects_call():
    assert _visit("oldnbr(x, op)") == "oldnbr(CALL, x, op)"


def test_align_injects_call():
    assert _visit("align(x)") == "align(CALL, x)"


def test_align_inplace_injects_call():
    assert _visit("align_inplace(x)") == "align_inplace(CALL, x)"


def test_sum_hood_injects_call():
    assert _visit("sum_hood(x)") == "sum_hood(CALL, x)"


def test_mean_hood_injects_call():
    assert _visit("mean_hood(x)") == "mean_hood(CALL, x)"


def test_all_hood_injects_call():
    assert _visit("all_hood(x)") == "all_hood(CALL, x)"


def test_any_hood_injects_call():
    assert _visit("any_hood(x)") == "any_hood(CALL, x)"


def test_list_hood_injects_call():
    r = _visit("list_hood(c, x)")
    assert "list_hood(CALL," in r


def test_abf_hops_injects_call():
    assert _visit("abf_hops(s)") == "abf_hops(CALL, s)"


def test_flex_distance_injects_call():
    r = _visit("flex_distance(s, e, r, d, f)")
    assert "flex_distance(CALL," in r


def test_bis_ksource_broadcast_injects_call():
    r = _visit("bis_ksource_broadcast(s, v, k, p, sp)")
    assert "bis_ksource_broadcast(CALL," in r


def test_gossip_min_injects_call():
    assert _visit("gossip_min(v)") == "gossip_min(CALL, v)"


def test_gossip_max_injects_call():
    assert _visit("gossip_max(v)") == "gossip_max(CALL, v)"


def test_gossip_mean_injects_call():
    assert _visit("gossip_mean(v)") == "gossip_mean(CALL, v)"


def test_list_idem_collection_injects_call():
    r = _visit("list_idem_collection(d, v, r, s, n, e, a)")
    assert "list_idem_collection(CALL," in r


def test_list_arith_collection_injects_call():
    r = _visit("list_arith_collection(d, v, r, s, n, e, a)")
    assert "list_arith_collection(CALL," in r


def test_follow_path_injects_call():
    r = _visit("follow_path(p, v, t)")
    assert "follow_path(CALL," in r


def test_follow_track_injects_call():
    assert _visit("follow_track(t)") == "follow_track(CALL, t)"


def test_random_rectangle_target_injects_call():
    r = _visit("random_rectangle_target(lo, hi)")
    assert "random_rectangle_target(CALL," in r


def test_neighbour_elastic_force_injects_call():
    r = _visit("neighbour_elastic_force(l, s)")
    assert "neighbour_elastic_force(CALL," in r


def test_diameter_election_injects_call():
    r = _visit("diameter_election(v, d)")
    assert "diameter_election(CALL," in r


def test_color_election_injects_call():
    assert _visit("color_election(v)") == "color_election(CALL, v)"


def test_wave_election_injects_call():
    assert _visit("wave_election(v)") == "wave_election(CALL, v)"


def test_constant_injects_call():
    assert _visit("constant(v)") == "constant(CALL, v)"


def test_counter_no_args_injects_call():
    assert _visit("counter()") == "counter(CALL)"


def test_delay_injects_call():
    r = _visit("delay(v, n)")
    assert "delay(CALL," in r


def test_toggle_injects_call():
    r = _visit("toggle(c)")
    assert "toggle(CALL," in r


def test_shared_clock_injects_call():
    assert _visit("shared_clock()") == "shared_clock(CALL)"


def test_timed_decay_injects_call():
    r = _visit("timed_decay(v, n, dt)")
    assert "timed_decay(CALL," in r


# ============================================================================
# Test 13: Primitive header mapping correctness
# ============================================================================


from fcpp_bridge.transpiler import _FCPP_PRIMITIVES


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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
