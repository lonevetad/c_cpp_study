"""Core transpiler — converts Python DSL to C++ code."""

import inspect
import ast
from typing import Type, Any, List, Dict, Optional
from pathlib import Path

from python_dsl.validators import AggregateValidator, ValidationError
from python_dsl.types import AggregateType, CppType


class TranspilationError(Exception):
    """Raised when transpilation fails."""

    pass


class CppCodeBuilder:
    """Accumulates C++ code fragments; emits complete program."""

    def __init__(self):
        self.includes: List[str] = []
        self.declarations: List[str] = []
        self.main_aggregate: str = ""
        self.helpers: List[str] = []

    def add_include(self, header: str) -> None:
        """Add #include directive."""
        if header not in self.includes:
            self.includes.append(header)

    def add_declaration(self, decl: str) -> None:
        """Add type/struct declaration."""
        self.declarations.append(decl)

    def set_main_aggregate(self, code: str) -> None:
        """Set the main aggregate function."""
        self.main_aggregate = code

    def add_helper(self, func: str) -> None:
        """Add helper function."""
        self.helpers.append(func)

    def build(self) -> str:
        """Emit complete C++ program."""
        lines: List[str] = []

        # Standard includes
        for inc in self.includes:
            lines.append(f"#include {inc}")

        if self.includes:
            lines.append("")

        # Type declarations
        for decl in self.declarations:
            lines.append(decl)
            lines.append("")

        # Helper functions
        for helper in self.helpers:
            lines.append(helper)
            lines.append("")

        # Main aggregate
        if self.main_aggregate:
            lines.append(self.main_aggregate)

        return "\n".join(lines)


class PythonAstVisitor(ast.NodeVisitor):
    """Visit Python AST nodes and translate to C++ expressions."""

    def __init__(self):
        self.variables: Dict[str, CppType] = {}
        self.errors: List[str] = []

    def visit_BinOp(self, node: ast.BinOp) -> str:
        """Translate binary operations: +, -, *, /, etc."""
        left = self.visit(node.left)
        right = self.visit(node.right)

        if isinstance(node.op, ast.Add):
            return f"({left} + {right})"
        elif isinstance(node.op, ast.Sub):
            return f"({left} - {right})"
        elif isinstance(node.op, ast.Mult):
            return f"({left} * {right})"
        elif isinstance(node.op, ast.Div):
            return f"({left} / {right})"
        elif isinstance(node.op, ast.Mod):
            return f"({left} % {right})"
        elif isinstance(node.op, ast.Pow):
            return f"std::pow({left}, {right})"
        else:
            self.errors.append(f"Unsupported binary operator: {node.op}")
            return "0"

    def visit_Compare(self, node: ast.Compare) -> str:
        """Translate comparisons: <, >, ==, etc."""
        left = self.visit(node.left)
        comparisons = []

        for op, comp in zip(node.ops, node.comparators):
            right = self.visit(comp)

            if isinstance(op, ast.Lt):
                comparisons.append(f"({left} < {right})")
            elif isinstance(op, ast.Gt):
                comparisons.append(f"({left} > {right})")
            elif isinstance(op, ast.Eq):
                comparisons.append(f"({left} == {right})")
            elif isinstance(op, ast.NotEq):
                comparisons.append(f"({left} != {right})")
            elif isinstance(op, ast.LtE):
                comparisons.append(f"({left} <= {right})")
            elif isinstance(op, ast.GtE):
                comparisons.append(f"({left} >= {right})")
            else:
                self.errors.append(f"Unsupported comparison: {op}")

            left = right

        return " && ".join(comparisons)

    def visit_Call(self, node: ast.Call) -> str:
        """Translate function calls."""
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
            args = [self.visit(arg) for arg in node.args]

            # Built-in functions
            if func_name == "max":
                return f"std::max({', '.join(args)})"
            elif func_name == "min":
                return f"std::min({', '.join(args)})"
            elif func_name == "sum":
                return f"std::accumulate({args[0]}.begin(), {args[0]}.end(), 0)"
            elif func_name == "len":
                return f"({args[0]}).size()"
            else:
                return f"{func_name}({', '.join(args)})"

        return "0"

    def visit_Constant(self, node: ast.Constant) -> str:
        """Translate constants: numbers, strings."""
        if isinstance(node.value, (int, float)):
            return str(node.value)
        elif isinstance(node.value, str):
            return f'"{node.value}"'
        elif node.value is None:
            return "nullptr"
        return str(node.value)

    def visit_Name(self, node: ast.Name) -> str:
        """Translate variable names."""
        return node.id

    def visit_Attribute(self, node: ast.Attribute) -> str:
        """Translate attribute access: obj.attr."""
        obj = self.visit(node.value)
        return f"{obj}.{node.attr}"

    def visit_Subscript(self, node: ast.Subscript) -> str:
        """Translate subscripts: arr[i]."""
        obj = self.visit(node.value)
        index = self.visit(node.slice)
        return f"{obj}[{index}]"

    def generic_visit(self, node: ast.AST) -> str:
        """Fallback for unsupported nodes."""
        self.errors.append(f"Unsupported AST node: {type(node).__name__}")
        return "0"


class Transpiler:
    """Main transpiler class: Python DSL → C++ code."""

    def __init__(self, aggregate_class: Type):
        """Initialize transpiler with aggregate function class."""
        self.aggregate_class = aggregate_class
        self.state_type: Optional[CppType] = None
        self._validate()

    def _validate(self) -> None:
        """Pre-flight checks."""
        warnings = AggregateValidator.validate(self.aggregate_class)
        for warning in warnings:
            print(f"[DSL] Warning: {warning}")

        self.state_type = AggregateType.infer(
            AggregateValidator.get_state_type(self.aggregate_class)
        )

    def generate(self) -> str:
        """
        Generate C++ code for this aggregate function.

        Returns complete C++ program as string.
        """
        builder = CppCodeBuilder()

        # Add standard FCPP includes
        builder.add_include("<fcpp/fcpp.hpp>")

        # Add state type declaration if custom struct
        if self.state_type.is_struct and self.state_type.fields:
            builder.add_declaration(self.state_type.cpp_declaration())

        # Generate compute function
        compute_code = self._generate_compute()
        builder.add_helper(compute_code)

        # Generate main aggregate function
        initial_code = self._generate_initial_state()
        main_agg = self._generate_main_aggregate(initial_code)
        builder.set_main_aggregate(main_agg)

        return builder.build()

    def _generate_initial_state(self) -> str:
        """Generate C++ code for initial_state() logic."""
        method = getattr(self.aggregate_class, "initial_state")
        source = inspect.getsource(method)

        # Extract return statement
        lines = source.split("\n")
        for line in lines:
            if "return" in line:
                # Very simple: just extract the value
                return_expr = line.split("return")[1].strip()
                return return_expr.rstrip(":")

        return "0"

    def _generate_compute(self) -> str:
        """Generate C++ compute function stub."""
        state_type_name = self.state_type.name if self.state_type else "double"

        return f"""
// Generated compute helper
{state_type_name} compute_next_state(
    const {state_type_name}& self_state,
    const std::vector<{state_type_name}>& neighbor_states) {{
    // TODO: Full transpilation in Phase 2
    if (neighbor_states.empty()) {{
        return self_state;
    }}
    return self_state;
}}
"""

    def _generate_main_aggregate(self, initial_expr: str) -> str:
        """Generate main FCPP aggregate function skeleton."""
        state_type_name = self.state_type.name if self.state_type else "double"

        return f"""
// Generated FCPP aggregate program
namespace fcpp_generated {{

AGGREGATE_TEMPLATE(main) : void {{
    using state_t = {state_type_name};

    node.state = {initial_expr};

    // Receive neighbor states via nbr()
    auto nbr_states = nbr<std::vector<state_t>>([](node_t& n) {{
        return std::vector<state_t>();  // TODO: collect neighbors
    }});

    // Compute next state
    node.state = compute_next_state(node.state, nbr_states);
}}

}}  // namespace fcpp_generated

// Entry point
MAIN() {{
    // TODO: Initialize FCPPSimulator
    // Run for specified rounds
}}
"""

    def get_state_type_cpp(self) -> CppType:
        """Get the inferred C++ state type."""
        return self.state_type or CppType("double")
