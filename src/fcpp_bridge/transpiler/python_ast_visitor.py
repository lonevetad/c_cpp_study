import ast
from typing import Dict, List

from fcpp_bridge.python_dsl.types import CppType
from fcpp_bridge.log import get_logger
from ._constants import _FCPP_PRIMITIVES

_log = get_logger(__name__)


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

            if func_name in _FCPP_PRIMITIVES:
                if func_name not in self.used_primitives:
                    self.used_primitives.append(func_name)
                if args:
                    return f"{func_name}(CALL, {', '.join(args)})"
                return f"{func_name}(CALL)"

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
        """
        params = ", ".join(f"auto {arg.arg}" for arg in node.args.args)
        body = self.visit(node.body)
        _log.debug("Transpiling lambda(%s) → [=](%s) { return %s; }", params, params, body)
        return f"[=]({params}) {{ return {body}; }}"

    def generic_visit(self, node: ast.AST) -> str:
        """Fallback for unsupported nodes."""
        self.errors.append(f"Unsupported AST node: {type(node).__name__}")
        return "0"
