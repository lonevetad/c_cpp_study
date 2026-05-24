"""Tests for Transpiler — full code generation and state type handling."""

import pytest
from dataclasses import dataclass
from fcpp_bridge.python_dsl import aggregate_function, Neighborhood, AggregateType, CppType
from fcpp_bridge.transpiler import Transpiler


# ============================================================================
# Test 2: Basic transpilation
# ============================================================================


def test_transpiler_simple_float():
    @aggregate_function
    class SimpleFloat:
        def initial_state(self) -> float:
            return 0.0

        def compute(self, self_state: float, neighbors: Neighborhood[float]) -> float:
            return self_state + 1.0

    cpp_code = Transpiler(SimpleFloat).generate()
    assert isinstance(cpp_code, str)
    assert len(cpp_code) > 0
    assert "#include <fcpp/fcpp.hpp>" in cpp_code
    assert "AGGREGATE_TEMPLATE(main)" in cpp_code


def test_transpiler_int_state():
    @aggregate_function
    class IntAggregate:
        def initial_state(self) -> int:
            return 0

        def compute(self, self_state: int, neighbors: Neighborhood[int]) -> int:
            return self_state

    assert "int" in Transpiler(IntAggregate).generate()


def test_transpiler_custom_struct():
    @dataclass
    class CustomState:
        x: float
        y: int

    @aggregate_function
    class StructAggregate:
        def initial_state(self) -> CustomState:
            return CustomState(0.0, 0)

        def compute(self, self_state: CustomState, neighbors: Neighborhood[CustomState]) -> CustomState:
            return self_state

    cpp_code = Transpiler(StructAggregate).generate()
    assert "struct CustomState" in cpp_code
    assert "double x" in cpp_code
    assert "int y" in cpp_code


# ============================================================================
# Test 4: Code generation
# ============================================================================


def test_transpiler_code_structure():
    @aggregate_function
    class TestAggregate:
        def initial_state(self) -> float:
            return 1.5

        def compute(self, self_state: float, neighbors: Neighborhood[float]) -> float:
            return self_state

    cpp_code = Transpiler(TestAggregate).generate()
    assert cpp_code.count("#include") > 0
    assert "AGGREGATE_TEMPLATE" in cpp_code
    assert "compute_next_state" in cpp_code


def test_transpiler_preserves_state_type():
    @aggregate_function
    class TypedAggregate:
        def initial_state(self) -> float:
            return 0.0

        def compute(self, self_state: float, neighbors: Neighborhood[float]) -> float:
            return self_state

    t = Transpiler(TypedAggregate)
    state_cpp_type = t.get_state_type_cpp()
    assert state_cpp_type.name == "double"
    assert state_cpp_type.is_primitive


# ============================================================================
# Test 9: AggregateType inference
# ============================================================================


def test_aggregate_type_infer_float():
    t = AggregateType.infer(float)
    assert t.name == "double"
    assert t.is_primitive


def test_aggregate_type_infer_int():
    t = AggregateType.infer(int)
    assert t.name == "int"
    assert t.is_primitive


def test_aggregate_type_infer_bool():
    t = AggregateType.infer(bool)
    assert t.name == "bool"
    assert t.is_primitive


def test_aggregate_type_infer_str():
    t = AggregateType.infer(str)
    assert t.name == "std::string"


def test_aggregate_type_infer_list_float():
    t = AggregateType.infer(list[float])
    assert "std::vector" in t.name
    assert "double" in t.name


def test_aggregate_type_infer_list_int():
    assert AggregateType.infer(list[int]).name == "std::vector<int>"


def test_aggregate_type_infer_tuple():
    t = AggregateType.infer(tuple[float, int])
    assert "std::tuple" in t.name
    assert "double" in t.name
    assert "int" in t.name


def test_aggregate_type_infer_dict():
    assert "std::map" in AggregateType.infer(dict[str, float]).name


def test_aggregate_type_infer_dataclass():
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
    assert AggregateType.is_numeric(CppType("double"))
    assert AggregateType.is_numeric(CppType("int"))
    assert not AggregateType.is_numeric(CppType("std::string"))


def test_aggregate_type_is_container():
    assert AggregateType.is_container(CppType("std::vector<int>"))
    assert AggregateType.is_container(CppType("std::map<int, int>"))
    assert not AggregateType.is_container(CppType("double"))


def test_cpp_type_declaration_primitive():
    t = CppType("double", is_primitive=True)
    assert t.cpp_declaration() == ""


def test_cpp_type_declaration_struct():
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

    assert "bool" in Transpiler(BoolAggregate).generate()


def test_transpiler_str_state():
    @aggregate_function
    class StrAggregate:
        def initial_state(self) -> str:
            return ""

        def compute(self, self_state: str, neighbors: Neighborhood[str]) -> str:
            return self_state

    assert "std::string" in Transpiler(StrAggregate).generate()


def test_transpiler_list_state():
    @aggregate_function
    class ListAggregate:
        def initial_state(self) -> list[float]:
            return []

        def compute(self, self_state: list[float], neighbors: Neighborhood[list[float]]) -> list[float]:
            return self_state

    assert "std::vector" in Transpiler(ListAggregate).generate()


def test_transpiler_includes_fcpp():
    @aggregate_function
    class FloatAgg:
        def initial_state(self) -> float:
            return 0.0

        def compute(self, self_state: float, neighbors: Neighborhood[float]) -> float:
            return self_state

    assert Transpiler(FloatAgg).generate().startswith("#include")


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

    assert Transpiler(IntAgg2).get_state_type_cpp().name == "int"


def test_transpiler_state_type_bool():
    @aggregate_function
    class BoolAgg2:
        def initial_state(self) -> bool:
            return True

        def compute(self, self_state: bool, neighbors: Neighborhood[bool]) -> bool:
            return self_state

    assert Transpiler(BoolAgg2).get_state_type_cpp().name == "bool"


def test_transpiler_custom_struct_field_types():
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


def test_transpiler_adds_header_for_used_primitive():
    @aggregate_function
    class MinHoodAgg:
        def initial_state(self) -> float:
            return 0.0
        def compute(self, self_state: float, neighbors: Neighborhood[float]) -> float:
            return min_hood(self_state)  # noqa: F821

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
