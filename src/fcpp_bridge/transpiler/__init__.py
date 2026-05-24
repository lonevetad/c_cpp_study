"""Core transpiler — converts Python DSL to C++ code."""

import inspect
import ast
from typing import Type, Any, List, Dict, Optional
from pathlib import Path

from fcpp_bridge.python_dsl.validators import AggregateValidator, ValidationError
from fcpp_bridge.python_dsl.types import AggregateType, CppType
from fcpp_bridge.log import get_logger

_log = get_logger(__name__)


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


# Maps each FCPP aggregate primitive to its FCPP coordination header.
_B = "<lib/coordination/basics.hpp>"
_U = "<lib/coordination/utils.hpp>"
_S = "<lib/coordination/spreading.hpp>"
_C = "<lib/coordination/collection.hpp>"
_G = "<lib/coordination/geometry.hpp>"
_E = "<lib/coordination/election.hpp>"
_T = "<lib/coordination/time.hpp>"

_FCPP_PRIMITIVES: Dict[str, str] = {
    # basics.hpp
    "nbr": _B, "old": _B, "nbr_uid": _B, "oldnbr": _B,
    "align": _B, "align_inplace": _B, "mod_other": _B,
    "fold_hood": _B, "count_hood": _B, "spawn": _B, "split": _B,
    # utils.hpp
    "min_hood": _U, "max_hood": _U, "sum_hood": _U, "mean_hood": _U,
    "all_hood": _U, "any_hood": _U, "list_hood": _U,
    # spreading.hpp
    "broadcast": _S, "abf_distance": _S, "abf_hops": _S,
    "bis_distance": _S, "flex_distance": _S, "bis_ksource_broadcast": _S,
    # collection.hpp
    "gossip": _C, "gossip_min": _C, "gossip_max": _C, "gossip_mean": _C,
    "sp_collection": _C, "mp_collection": _C, "wmp_collection": _C,
    "list_idem_collection": _C, "list_arith_collection": _C,
    # geometry.hpp
    "follow_target": _G, "follow_path": _G, "follow_track": _G,
    "rectangle_walk": _G, "random_rectangle_target": _G,
    "neighbour_elastic_force": _G, "neighbour_gravitational_force": _G,
    "neighbour_charged_force": _G, "line_elastic_force": _G,
    "plane_elastic_force": _G, "point_elastic_force": _G,
    "point_gravitational_force": _G,
    # election.hpp
    "diameter_election": _E, "diameter_election_distance": _E,
    "color_election": _E, "color_election_distance": _E,
    "wave_election": _E, "wave_election_distance": _E,
    # time.hpp
    "constant": _T, "constant_after": _T, "counter": _T, "delay": _T,
    "round_since": _T, "time_since": _T, "timed_decay": _T,
    "exponential_filter": _T, "shared_clock": _T, "shared_decay": _T,
    "shared_filter": _T, "toggle": _T, "toggle_filter": _T,
}


class PythonAstVisitor(ast.NodeVisitor):
    """Visit Python AST nodes and translate to C++ expressions."""

    def __init__(self):
        self.variables: Dict[str, CppType] = {}
        self.errors: List[str] = []
        self.used_primitives: List[str] = []

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

            # FCPP aggregate primitives — inject CALL as first argument
            if func_name in _FCPP_PRIMITIVES:
                if func_name not in self.used_primitives:
                    self.used_primitives.append(func_name)
                if args:
                    return f"{func_name}(CALL, {', '.join(args)})"
                return f"{func_name}(CALL)"

            # Python built-in mappings
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

    def visit_Lambda(self, node: ast.Lambda) -> str:
        """Translate a Python lambda to a C++14 generic lambda for G&& parameters.

        ``lambda a, b: a + b``  →  ``[=](auto a, auto b) { return (a + b); }``

        Capture-by-value (``[=]``) is safe because FCPP calls the callable
        immediately within the same scope — nothing is stored after return.
        """
        params = ", ".join(f"auto {arg.arg}" for arg in node.args.args)
        body = self.visit(node.body)
        _log.debug("Transpiling lambda(%s) → [=](%s) { return %s; }", params, params, body)
        return f"[=]({params}) {{ return {body}; }}"

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
            _log.warning("DSL: %s", warning)

        self.state_type = AggregateType.infer(
            AggregateValidator.get_state_type(self.aggregate_class)
        )

    def generate(self) -> str:
        """Generate C++ code for this aggregate function.

        Returns complete C++ program as string.
        """
        _log.debug("Generating C++ for %s", self.aggregate_class.__name__)
        builder = CppCodeBuilder()

        # Add standard FCPP includes
        builder.add_include("<fcpp/fcpp.hpp>")

        # Auto-add headers required by the state type (e.g. <optional>, <set>)
        for inc in (self.state_type.required_includes or []):
            builder.add_include(inc)

        # Add state type declaration if custom struct
        if self.state_type.is_struct and self.state_type.fields:
            builder.add_declaration(self.state_type.cpp_declaration())

        # Generate compute function (may populate used_primitives via PythonAstVisitor)
        compute_code, used_prims = self._generate_compute()
        for prim in used_prims:
            header = _FCPP_PRIMITIVES.get(prim)
            if header:
                builder.add_include(header)
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

    def _generate_compute(self):
        """Transpile the Python compute() body to a C++ helper function.

        Returns (code_str, used_primitives_list).

        Extracts the return expression from the aggregate class's compute()
        method, runs it through PythonAstVisitor, and wraps it in a typed
        C++ function.  Parameter names are remapped:
          self_state / state / s  → self_state
          neighbors / nbrs / neighborhood → neighbor_states
        """
        state_type_name = self.state_type.name if self.state_type else "double"
        method = getattr(self.aggregate_class, "compute")

        return_expr_cpp, used_prims = self._transpile_method_return(method, {
            "self_state": "self_state",
            "state": "self_state",
            "s": "self_state",
            "neighbors": "neighbor_states",
            "nbrs": "neighbor_states",
            "neighborhood": "neighbor_states",
        })

        code = (
            f"\n// Generated compute helper (transpiled from Python)\n"
            f"{state_type_name} compute_next_state(\n"
            f"    const {state_type_name}& self_state,\n"
            f"    const std::vector<{state_type_name}>& neighbor_states) {{\n"
            f"    return {return_expr_cpp};\n"
            f"}}\n"
        )
        return code, used_prims

    def _transpile_method_return(self, method, param_remap: dict):
        """Extract the return expression from a Python method and transpile it.

        Returns (expr_cpp_str, used_primitives_list).

        Parses the method source, finds the return statement, runs it through
        PythonAstVisitor, then applies param_remap substitutions so that the
        Python parameter names become C++ variable names.
        """
        import textwrap as _tw
        import re

        try:
            source = inspect.getsource(method)
            source = _tw.dedent(source)
            tree = ast.parse(source)
            func_def = tree.body[0]  # FunctionDef
        except (OSError, SyntaxError, IndexError):
            return "self_state", []

        # Find the first return statement (depth-first)
        for node in ast.walk(func_def):
            if isinstance(node, ast.Return) and node.value is not None:
                visitor = PythonAstVisitor()
                expr_cpp = visitor.visit(node.value)
                for py_name, cpp_name in param_remap.items():
                    expr_cpp = re.sub(
                        rf'\b{re.escape(py_name)}\b', cpp_name, expr_cpp
                    )
                return expr_cpp, visitor.used_primitives

        return "self_state", []

    def _generate_main_aggregate(self, initial_expr: str) -> str:
        """Generate the main FCPP aggregate function.

        Wires up:
        - Initial state from initial_state()
        - Neighbor collection via FCPP nbr<>()
        - State update via compute_next_state()
        - IPC server loop for Python ↔ C++ communication
        """
        state_type_name = self.state_type.name if self.state_type else "double"
        class_name = self.aggregate_class.__name__

        return f"""
// Generated FCPP aggregate program — {class_name}
namespace fcpp_generated {{

AGGREGATE_TEMPLATE(main) : void {{
    using state_t = {state_type_name};

    // Initialize or retrieve persistent state
    auto& current_state = old(CALL, static_cast<state_t>({initial_expr}));

    // Collect neighbor states via nbr
    auto nbr_states = nbr(CALL, current_state);

    // Flatten field to vector for compute helper
    std::vector<state_t> neighbor_vec;
    fold_hood(CALL, [&](state_t v, fcpp::unit) {{
        neighbor_vec.push_back(v);
        return fcpp::unit{{}};
    }}, fcpp::unit{{}}, nbr_states);

    // Compute next state from transpiled Python logic
    current_state = compute_next_state(current_state, neighbor_vec);
}}

}}  // namespace fcpp_generated

// Entry point — spawns IPC server then runs simulation
int main(int argc, char* argv[]) {{
    int num_nodes = (argc > 1) ? std::atoi(argv[1]) : 100;
    int ipc_port  = (argc > 2) ? std::atoi(argv[2]) : 8765;

    // TODO: initialise FCPPSimulator with num_nodes and ipc_port
    // auto sim = fcpp_runtime::SwarmSimulator<fcpp_generated::main>(num_nodes, ipc_port);
    // sim.run_until(1e9);
    return 0;
}}
"""

    def get_state_type_cpp(self) -> CppType:
        """Get the inferred C++ state type."""
        return self.state_type or CppType("double")
