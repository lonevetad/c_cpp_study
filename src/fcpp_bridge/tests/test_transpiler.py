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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
