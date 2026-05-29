import ast
from typing import Dict, List, Set

from fcpp_bridge.python_dsl.types import CppType
from fcpp_bridge.log import get_logger
from ._constants import _FCPP_PRIMITIVES

_log = get_logger(__name__)


class PythonAstVisitor(ast.NodeVisitor):
    """Visit Python AST nodes and translate to C++ expressions and statements."""

    def __init__(self, constants: dict = None):
        self.variables: Dict[str, CppType] = {}
        self.errors: List[str] = []
        self.used_primitives: List[str] = []
        self.declared_vars: Set[str] = set()
        # Optional namespace for constant-folding dotted attribute chains.
        # When provided (typically the compute() function's __globals__), any
        # dotted name that resolves to an int/float is emitted as a literal,
        # which is required for valid C++ case labels (e.g. WorkerRole.X.value).
        self.constants: dict = constants if constants is not None else {}

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
        """Translate function calls (positional and keyword arguments)."""
        if isinstance(node.func, ast.Name):
            func_name = node.func.id

            # frozenset({x, y}) → set_t{x, y};  frozenset() → set_t{}
            # Must be checked before generic arg-visiting (inner Set literal has no visitor).
            if func_name == "frozenset":
                if node.args and isinstance(node.args[0], ast.Set):
                    elems = [self.visit(e) for e in node.args[0].elts]
                    return f"set_t{{{', '.join(elems)}}}" if elems else "set_t{}"
                return "set_t{}"

            # min_hood/max_hood with a single Tuple arg → std::make_tuple(...)
            # Avoids the C++ comma-expression pitfall: (a, b) evaluates to b.
            # Note: callers that use a component of the result still need
            # std::get<N>(tup) manually — that extraction cannot be automated
            # without type inference.
            if func_name in ("min_hood", "max_hood") and len(node.args) == 1:
                if isinstance(node.args[0], ast.Tuple):
                    elems = [self.visit(e) for e in node.args[0].elts]
                    if func_name not in self.used_primitives:
                        self.used_primitives.append(func_name)
                    return f"{func_name}(CALL, std::make_tuple({', '.join(elems)}))"

            args = [self.visit(arg) for arg in node.args]
            # keyword args: emit values positionally (keyword names are discarded)
            args += [self.visit(kw.value)
                     for kw in node.keywords if kw.arg is not None]

            if func_name in _FCPP_PRIMITIVES:
                if func_name not in self.used_primitives:
                    self.used_primitives.append(func_name)
                if args:
                    return f"{func_name}(CALL, {', '.join(args)})"
                return f"{func_name}(CALL)"

            if func_name == "self_uid":
                # self_uid() → node.uid (direct field access; no CALL counter)
                return "node.uid"

            if func_name == "max":
                return f"std::max({', '.join(args)})"
            elif func_name == "min":
                return f"std::min({', '.join(args)})"
            elif func_name == "sum":
                return f"std::accumulate({args[0]}.begin(), {args[0]}.end(), 0)"
            elif func_name == "len":
                return f"({args[0]}).size()"
            elif func_name == "abs":
                return f"std::abs({args[0]})"
            elif func_name == "float":
                return f"static_cast<double>({args[0]})"
            elif func_name == "int":
                return f"static_cast<int>({args[0]})"
            elif func_name == "bool":
                return f"static_cast<bool>({args[0]})"
            else:
                return f"{func_name}({', '.join(args)})"

        if isinstance(node.func, ast.Attribute):
            obj = self.visit(node.func.value)
            method = node.func.attr
            args = [self.visit(arg) for arg in node.args]
            args += [self.visit(kw.value)
                     for kw in node.keywords if kw.arg is not None]
            return f"{obj}.{method}({', '.join(args)})"

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

    def _resolve_dotted_chain(self, node: ast.Attribute):
        """Walk an Attribute chain and resolve it against self.constants.

        Returns the resolved Python value if the full chain resolves, else None.
        Only the root name is looked up in self.constants; subsequent attrs are
        resolved via getattr().  Useful for folding IntEnum member values to
        integer literals so that C++ case labels remain compile-time constants.
        """
        parts = []
        current = node
        while isinstance(current, ast.Attribute):
            parts.append(current.attr)
            current = current.value
        if not isinstance(current, ast.Name):
            return None
        parts.append(current.id)
        parts.reverse()  # [root, attr1, attr2, ...]

        root = parts[0]
        if root not in self.constants:
            return None
        obj = self.constants[root]
        try:
            for attr in parts[1:]:
                obj = getattr(obj, attr)
        except AttributeError:
            return None
        return obj

    def visit_Attribute(self, node: ast.Attribute) -> str:
        """Translate attribute access: obj.attr.

        When a constants dict is available, attempts to resolve the full dotted
        chain (e.g. ``WorkerRole.RECEIVER.value``) to its numeric literal value.
        This is required for C++ case labels, which must be compile-time constants.
        bool is mapped to 1/0 rather than true/false to preserve integer type.
        """
        if self.constants:
            resolved = self._resolve_dotted_chain(node)
            if resolved is True:
                return "1"
            elif resolved is False:
                return "0"
            elif isinstance(resolved, int):
                return str(resolved)
            elif isinstance(resolved, float):
                return str(resolved)
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
        _log.debug(
            "Transpiling lambda(%s) → [=](%s) { return %s; }", params, params, body)
        return f"[=]({params}) {{ return {body}; }}"

    # ── Expression nodes ──────────────────────────────────────────────────────

    def visit_IfExp(self, node: ast.IfExp) -> str:
        """Translate Python ternary `a if cond else b` → `(cond ? a : b)`."""
        test = self.visit(node.test)
        body = self.visit(node.body)
        orelse = self.visit(node.orelse)
        return f"({test} ? {body} : {orelse})"

    def visit_BoolOp(self, node: ast.BoolOp) -> str:
        """Translate `and`/`or` → `&&`/`||`."""
        op = "&&" if isinstance(node.op, ast.And) else "||"
        parts = [self.visit(v) for v in node.values]
        return "(" + f" {op} ".join(parts) + ")"

    def visit_UnaryOp(self, node: ast.UnaryOp) -> str:
        """Translate unary `not`/`-`/`+` → C++ `!`/`-`/`+`."""
        operand = self.visit(node.operand)
        if isinstance(node.op, ast.Not):
            return f"(!{operand})"
        elif isinstance(node.op, ast.USub):
            return f"(-{operand})"
        elif isinstance(node.op, ast.UAdd):
            return f"(+{operand})"
        else:
            self.errors.append(
                f"Unsupported unary operator: {type(node.op).__name__}")
            return "0"

    def visit_List(self, node: ast.List) -> str:
        """Translate Python list literal `[a, b]` → `{a, b}`."""
        elements = [self.visit(e) for e in node.elts]
        return "{" + ", ".join(elements) + "}"

    def visit_Tuple(self, node: ast.Tuple) -> str:
        """Translate Python tuple `(a, b)` → `{a, b}` (struct-init style)."""
        elements = [self.visit(e) for e in node.elts]
        return "{" + ", ".join(elements) + "}"

    # ── Statement nodes ───────────────────────────────────────────────────────

    def visit_Expr(self, node: ast.Expr) -> str:
        """Translate expression statement (e.g. bare function call)."""
        return f"{self.visit(node.value)};"

    def visit_Return(self, node: ast.Return) -> str:
        """Translate `return expr` → `return expr;`."""
        if node.value is None:
            return "return;"
        return f"return {self.visit(node.value)};"

    def visit_Assign(self, node: ast.Assign) -> str:
        """Translate `x = expr` → `auto x = expr;` (first use) or `x = expr;`."""
        if len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            name = node.targets[0].id
            value = self.visit(node.value)
            if name not in self.declared_vars:
                self.declared_vars.add(name)
                return f"auto {name} = {value};"
            return f"{name} = {value};"
        self.errors.append(
            f"Unsupported assignment target: {ast.dump(node.targets[0])}")
        return ""

    def visit_AnnAssign(self, node: ast.AnnAssign) -> str:
        """Translate annotated assignment `x: T = expr` → `auto x = expr;`."""
        if node.value is None:
            return ""
        if not isinstance(node.target, ast.Name):
            self.errors.append("Unsupported annotated assignment target")
            return ""
        name = node.target.id
        value = self.visit(node.value)
        if name not in self.declared_vars:
            self.declared_vars.add(name)
            return f"auto {name} = {value};"
        return f"{name} = {value};"

    def visit_AugAssign(self, node: ast.AugAssign) -> str:
        """Translate `x += y` → `x += y;`."""
        target = self.visit(node.target)
        value = self.visit(node.value)
        _ops = {
            ast.Add: "+=", ast.Sub: "-=", ast.Mult: "*=",
            ast.Div: "/=", ast.Mod: "%=",
        }
        op_str = _ops.get(type(node.op), "+=")
        return f"{target} {op_str} {value};"

    def visit_If(self, node: ast.If) -> str:
        """Translate if/elif/else to C++ if/else if/else."""
        test = self.visit(node.test)
        body = self.transpile_statements(node.body)
        result = f"if ({test}) {{\n{body}\n}}"
        if node.orelse:
            if len(node.orelse) == 1 and isinstance(node.orelse[0], ast.If):
                # elif chain
                inner = self.visit(node.orelse[0])
                result += f" else {inner}"
            else:
                orelse = self.transpile_statements(node.orelse)
                result += f" else {{\n{orelse}\n}}"
        return result

    def visit_While(self, node: ast.While) -> str:
        """Translate `while cond: ...` → C++ `while (cond) { ... }`."""
        test = self.visit(node.test)
        body = self.transpile_statements(node.body)
        return f"while ({test}) {{\n{body}\n}}"

    def visit_For(self, node: ast.For) -> str:
        """Translate `for i in range(...)` → C++ for loop."""
        if (
            isinstance(node.iter, ast.Call)
            and isinstance(node.iter.func, ast.Name)
            and node.iter.func.id == "range"
        ):
            var = node.target.id if isinstance(node.target, ast.Name) else "i"
            args = node.iter.args
            if len(args) == 1:
                end = self.visit(args[0])
                header = f"int {var} = 0; {var} < {end}; ++{var}"
            elif len(args) == 2:
                start, end = self.visit(args[0]), self.visit(args[1])
                header = f"int {var} = {start}; {var} < {end}; ++{var}"
            elif len(args) == 3:
                start, end, step = (self.visit(a) for a in args)
                header = f"int {var} = {start}; {var} < {end}; {var} += {step}"
            else:
                self.errors.append("range() requires 1-3 arguments")
                return ""
            body = self.transpile_statements(node.body)
            return f"for ({header}) {{\n{body}\n}}"
        self.errors.append(
            "Only range()-based for loops are supported by the transpiler")
        return ""

    def visit_Match(self, node: ast.Match) -> str:
        """Translate Python ``match/case`` (3.10+) → C++ ``switch``.

        Supported patterns:
        - ``case X:``          — value pattern → ``case X:``
        - ``case _:``          — wildcard     → ``default:``
        - ``case X | Y:``      — OR pattern   → ``case X: case Y:`` (C++ fallthrough labels)
        - ``case X if cond:``  — guard clause → ``case X: if (cond) { ... }``

        Guard clauses wrap the case body in an ``if`` block; the ``break`` still
        follows so unmatched guards fall out of the switch rather than falling
        through.  This mirrors C++17 ``[[fallthrough]]`` avoidance and keeps
        the generated code compatible with C++14.
        """
        subject = self.visit(node.subject)
        cases_cpp: List[str] = []
        for case in node.cases:
            body = self.transpile_statements(case.body)
            pattern = case.pattern

            # Guard clause: `case X if cond:` → wrap body in `if (cond) { ... }`
            if case.guard is not None:
                guard_cpp = self.visit(case.guard)
                body = f"if ({guard_cpp}) {{\n{body}\n    }}"

            if (
                isinstance(pattern, ast.MatchAs)
                and pattern.name is None
                and pattern.pattern is None
            ):
                # wildcard `case _:` → default
                cases_cpp.append(f"default:\n{body}\n    break;")
            elif isinstance(pattern, ast.MatchValue):
                val = self.visit(pattern.value)
                cases_cpp.append(f"case {val}:\n{body}\n    break;")
            elif isinstance(pattern, ast.MatchOr):
                # OR pattern `case A | B | C:` → `case A: case B: case C:` (shared body)
                labels: List[str] = []
                for sub in pattern.patterns:
                    if isinstance(sub, ast.MatchValue):
                        labels.append(f"case {self.visit(sub.value)}:")
                    else:
                        self.errors.append(
                            f"Unsupported OR sub-pattern: {type(sub).__name__}"
                        )
                if labels:
                    cases_cpp.append(
                        "\n".join(labels) + f"\n{body}\n    break;"
                    )
            else:
                self.errors.append(
                    f"Unsupported match pattern: {type(pattern).__name__}"
                )
        if not any(c.startswith("default") for c in cases_cpp):
            cases_cpp.append("default: break;")
        inner = "\n".join(cases_cpp)
        return f"switch ({subject}) {{\n{inner}\n}}"

    def visit_Pass(self, node: ast.Pass) -> str:
        """Translate `pass` → empty (C++ needs no statement)."""
        return ""

    def visit_Break(self, node: ast.Break) -> str:
        """Translate `break` → `break;`."""
        return "break;"

    def visit_Continue(self, node: ast.Continue) -> str:
        """Translate `continue` → `continue;`."""
        return "continue;"

    # ── Statement list helper ─────────────────────────────────────────────────

    def transpile_statements(self, stmts: list, indent: int = 4) -> str:
        """Transpile a list of AST statement nodes into indented C++ lines."""
        indent_str = " " * indent
        lines: List[str] = []
        for stmt in stmts:
            code = self.visit(stmt)
            if not code:
                continue
            for line in code.split("\n"):
                lines.append(f"{indent_str}{line}")
        return "\n".join(lines)

    # ── Fallback ──────────────────────────────────────────────────────────────

    def generic_visit(self, node: ast.AST) -> str:
        """Fallback for unsupported nodes."""
        self.errors.append(f"Unsupported AST node: {type(node).__name__}")
        return "0"
