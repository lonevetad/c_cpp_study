"""Language parser — accept aggregate programs from strings/files."""

from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass


@dataclass
class AstNode:
    """Simplified AST node for aggregate programs."""

    node_type: str  # "program", "function", "expr", "statement"
    name: Optional[str] = None
    value: Any = None
    children: List["AstNode"] = None

    def __post_init__(self):
        if self.children is None:
            self.children = []


class ParserError(Exception):
    """Raised when parsing fails."""

    pass


class AggregateLanguageParser:
    """
    Parse aggregate programs from strings or files.

    Phase 5: ANTLR integration (currently simplified Python parser)

    Example grammar:
    ```
    aggregate_program:
        function_def+

    function_def:
        'def' NAME ':' initial_state_def compute_def

    initial_state_def:
        'initial_state' ':' expr

    compute_def:
        'compute' '(' self_param ',' nbr_param ')' ':' expr

    expr:
        binary_expr | call_expr | atom
    ```
    """

    def __init__(self):
        self.tokens: List[str] = []
        self.pos = 0

    def parse_string(self, program_str: str) -> AstNode:
        """
        Parse program from string.

        Args:
            program_str: Aggregate program text

        Returns:
            AST (Abstract Syntax Tree)

        Raises:
            ParserError: if parsing fails
        """
        self._tokenize(program_str)
        self.pos = 0

        try:
            program = self._parse_program()
            if self.pos < len(self.tokens):
                raise ParserError(f"Unexpected token: {self.tokens[self.pos]}")
            return program
        except (IndexError, ValueError) as e:
            raise ParserError(f"Parse error: {e}")

    def parse_file(self, filepath: Path) -> AstNode:
        """Parse program from file."""
        with open(filepath) as f:
            return self.parse_string(f.read())

    # ========================================================================
    # Tokenizer
    # ========================================================================

    def _tokenize(self, program_str: str) -> None:
        """Tokenize program string."""
        import re

        # Token patterns
        patterns = [
            (r"#.*$", "COMMENT"),  # Comments
            (r"\s+", "WHITESPACE"),  # Whitespace
            (r"\bdef\b", "DEF"),
            (r"\binitial_state\b", "INITIAL"),
            (r"\bcompute\b", "COMPUTE"),
            (r"\bif\b", "IF"),
            (r"\breturn\b", "RETURN"),
            (r"\b(nbr|old|nbr_uid|oldnbr|align|align_inplace|mod_other|split"
             r"|fold_hood|count_hood|spawn"
             r"|min_hood|max_hood|sum_hood|mean_hood|all_hood|any_hood|list_hood"
             r"|abf_distance|abf_hops|bis_distance|flex_distance|broadcast|bis_ksource_broadcast"
             r"|gossip|gossip_min|gossip_max|gossip_mean"
             r"|sp_collection|mp_collection|wmp_collection|list_idem_collection|list_arith_collection"
             r"|follow_target|follow_path|follow_track|random_rectangle_target|rectangle_walk"
             r"|neighbour_elastic_force|neighbour_gravitational_force|neighbour_charged_force"
             r"|line_elastic_force|plane_elastic_force|point_elastic_force|point_gravitational_force"
             r"|diameter_election|diameter_election_distance"
             r"|color_election|color_election_distance"
             r"|wave_election|wave_election_distance"
             r"|constant|constant_after|counter|delay|round_since|time_since"
             r"|timed_decay|exponential_filter|shared_clock|shared_decay|shared_filter"
             r"|toggle|toggle_filter)\b", "PRIMITIVE"),
            (r"\b[a-zA-Z_]\w*\b", "NAME"),
            (r"\d+\.\d+", "FLOAT"),
            (r"\d+", "INT"),
            (r'"[^"]*"', "STRING"),
            (r"[+\-*/=<>!&|()[\]{},;:.]", "OP"),
        ]

        # Compile regex
        regex = "|".join(f"({p})" for p, _ in patterns)
        tokens_raw = []

        for match in re.finditer(regex, program_str, re.MULTILINE):
            token_str = match.group()
            token_type = None

            for pattern, ttype in patterns:
                if re.match(pattern, token_str):
                    token_type = ttype
                    break

            if token_type not in ("COMMENT", "WHITESPACE"):
                tokens_raw.append(token_str)

        self.tokens = tokens_raw

    # ========================================================================
    # Parser
    # ========================================================================

    def _current_token(self) -> Optional[str]:
        """Get current token without advancing."""
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return None

    def _peek_token(self, offset: int = 1) -> Optional[str]:
        """Look ahead at next token."""
        if self.pos + offset < len(self.tokens):
            return self.tokens[self.pos + offset]
        return None

    def _consume(self, expected: Optional[str] = None) -> str:
        """Consume and return current token."""
        token = self._current_token()
        if expected and token != expected:
            raise ParserError(f"Expected '{expected}', got '{token}'")
        if token is None:
            raise ParserError("Unexpected end of input")
        self.pos += 1
        return token

    def _parse_program(self) -> AstNode:
        """Parse: aggregate_program = function_def+"""
        functions = []

        while self.pos < len(self.tokens):
            functions.append(self._parse_function())

        return AstNode(node_type="program", children=functions)

    def _parse_function(self) -> AstNode:
        """Parse: def NAME: initial_state_def compute_def"""
        self._consume("def")
        name = self._consume()  # function name

        self._consume(":")

        # Parse initial_state
        initial_state = self._parse_initial_state()

        # Parse compute
        compute = self._parse_compute()

        return AstNode(
            node_type="function",
            name=name,
            children=[initial_state, compute],
        )

    def _parse_initial_state(self) -> AstNode:
        """Parse: initial_state: expr"""
        self._consume("initial_state")
        self._consume(":")

        expr = self._parse_expr()
        return AstNode(node_type="initial_state", children=[expr])

    def _parse_compute(self) -> AstNode:
        """Parse: compute(self_state, neighbors): expr"""
        self._consume("compute")
        self._consume("(")

        self_param = self._consume()  # self_state
        self._consume(",")
        nbr_param = self._consume()  # neighbors

        self._consume(")")
        self._consume(":")

        expr = self._parse_expr()
        return AstNode(
            node_type="compute",
            children=[expr],
        )

    def _parse_expr(self) -> AstNode:
        """Parse binary/ternary/primary expressions."""
        return self._parse_binary_expr()

    def _parse_binary_expr(self) -> AstNode:
        """Parse: expr op expr op expr..."""
        left = self._parse_call_expr()

        while self._current_token() in ("+", "-", "*", "/", "==", "!=", "<", ">"):
            op = self._consume()
            right = self._parse_call_expr()
            left = AstNode(
                node_type="binop",
                value=op,
                children=[left, right],
            )

        return left

    # All recognised FCPP aggregate primitives.
    _ALL_PRIMITIVES = frozenset({
        # basics.hpp
        "nbr", "old", "nbr_uid", "oldnbr", "align", "align_inplace",
        "mod_other", "split", "fold_hood", "count_hood", "spawn",
        # utils.hpp
        "min_hood", "max_hood", "sum_hood", "mean_hood",
        "all_hood", "any_hood", "list_hood",
        # spreading.hpp
        "abf_distance", "abf_hops", "bis_distance", "flex_distance",
        "broadcast", "bis_ksource_broadcast",
        # collection.hpp
        "gossip", "gossip_min", "gossip_max", "gossip_mean",
        "sp_collection", "mp_collection", "wmp_collection",
        "list_idem_collection", "list_arith_collection",
        # geometry.hpp
        "follow_target", "follow_path", "follow_track",
        "random_rectangle_target", "rectangle_walk",
        "neighbour_elastic_force", "neighbour_gravitational_force", "neighbour_charged_force",
        "line_elastic_force", "plane_elastic_force",
        "point_elastic_force", "point_gravitational_force",
        # election.hpp
        "diameter_election", "diameter_election_distance",
        "color_election", "color_election_distance",
        "wave_election", "wave_election_distance",
        # time.hpp
        "constant", "constant_after", "counter", "delay",
        "round_since", "time_since", "timed_decay", "exponential_filter",
        "shared_clock", "shared_decay", "shared_filter",
        "toggle", "toggle_filter",
    })

    def _parse_call_expr(self) -> AstNode:
        """Parse: PRIMITIVE ( argList? ) | atom"""
        if self._current_token() in AggregateLanguageParser._ALL_PRIMITIVES:
            primitive = self._consume()
            self._consume("(")
            args: List[AstNode] = []
            if self._current_token() != ")":
                args.append(self._parse_expr())
                while self._current_token() == ",":
                    self._consume(",")
                    args.append(self._parse_expr())
            self._consume(")")
            return AstNode(node_type="call", name=primitive, children=args)

        return self._parse_atom()

    def _parse_atom(self) -> AstNode:
        """Parse: NAME | NUMBER | STRING | ( expr )"""
        token = self._current_token()

        if token == "(":
            self._consume("(")
            expr = self._parse_expr()
            self._consume(")")
            return expr

        if token and token[0].isdigit():
            value = self._consume()
            if "." in value:
                return AstNode(node_type="float", value=float(value))
            return AstNode(node_type="int", value=int(value))

        if token and token[0].isalpha():
            name = self._consume()
            return AstNode(node_type="name", value=name)

        raise ParserError(f"Unexpected token: {token}")


class AntlrParser:
    """
    ANTLR4-backed parser for aggregate programs.

    Uses the generated stubs in ``__antlr_gen/`` when the ``antlr4`` Python
    runtime is installed; otherwise falls back to ``AggregateLanguageParser``.

    Generate stubs once with::

        java -jar antlr-4.13.1-complete.jar \\
            -Dlanguage=Python3 \\
            -o src/fcpp_bridge/grammar/__antlr_gen \\
            src/fcpp_bridge/grammar/AggregateProgram.g4

    Install runtime::

        pip install antlr4-python3-runtime==4.13.1
    """

    def __init__(self):
        self._antlr_available = self._check_antlr()
        self._fallback = AggregateLanguageParser()

    @staticmethod
    def _check_antlr() -> bool:
        """Return True if antlr4 runtime and generated stubs are both available."""
        try:
            import antlr4  # noqa: F401
        except ImportError:
            return False

        try:
            import sys
            from pathlib import Path as _Path
            gen_dir = str(_Path(__file__).parent / "__antlr_gen")
            if gen_dir not in sys.path:
                sys.path.insert(0, gen_dir)
            from AggregateProgramLexer import AggregateProgramLexer as _  # type: ignore  # noqa: F401
            from AggregateProgramParser import AggregateProgramParser as _  # type: ignore  # noqa: F401
        except ImportError:
            return False

        return True

    def parse_string(self, program_str: str) -> AstNode:
        """
        Parse aggregate program from string.

        Delegates to the ANTLR4 runtime when available; falls back to the
        hand-written ``AggregateLanguageParser`` otherwise.
        """
        if self._antlr_available:
            return self._parse_with_antlr(program_str)
        return self._fallback.parse_string(program_str)

    def parse_file(self, filepath: Path) -> AstNode:
        """Parse aggregate program from file."""
        with open(filepath) as fh:
            return self.parse_string(fh.read())

    def _parse_with_antlr(self, program_str: str) -> AstNode:
        """Parse via generated ANTLR4 stubs and convert to AstNode tree."""
        import antlr4
        from AggregateProgramLexer import AggregateProgramLexer  # type: ignore
        from AggregateProgramParser import AggregateProgramParser  # type: ignore

        input_stream = antlr4.InputStream(program_str)
        lexer = AggregateProgramLexer(input_stream)
        token_stream = antlr4.CommonTokenStream(lexer)
        parser = AggregateProgramParser(token_stream)

        # Attach error listener that raises ParserError
        class _ErrorListener(antlr4.error.ErrorListener.ErrorListener):
            def syntaxError(self, recognizer, offendingSymbol, line, column, msg, e):
                raise ParserError(f"line {line}:{column} {msg}")

        lexer.removeErrorListeners()
        parser.removeErrorListeners()
        lexer.addErrorListener(_ErrorListener())
        parser.addErrorListener(_ErrorListener())

        tree = parser.aggregateProgram()
        return self._ctx_to_ast(tree)

    def _ctx_to_ast(self, ctx: Any) -> AstNode:
        """Recursively convert an ANTLR4 parse-tree context to AstNode."""
        import antlr4

        class_name = type(ctx).__name__

        if class_name == "AggregateProgramContext":
            children = [self._ctx_to_ast(c) for c in ctx.functionDef()]
            return AstNode(node_type="program", children=children)

        if class_name == "FunctionDefContext":
            name = ctx.NAME().getText()
            initial = self._ctx_to_ast(ctx.initialStateDef())
            compute = self._ctx_to_ast(ctx.computeDef())
            return AstNode(node_type="function", name=name, children=[initial, compute])

        if class_name == "InitialStateDefContext":
            expr = self._ctx_to_ast(ctx.expr())
            return AstNode(node_type="initial_state", children=[expr])

        if class_name == "ComputeDefContext":
            expr = self._ctx_to_ast(ctx.expr())
            return AstNode(node_type="compute", children=[expr])

        if class_name in ("BinaryExprContext", "CompareExprContext"):
            left = self._ctx_to_ast(ctx.expr(0))
            right = self._ctx_to_ast(ctx.expr(1))
            op = ctx.op.text
            return AstNode(node_type="binop", value=op, children=[left, right])

        if class_name == "PrimCallContext":
            return self._ctx_to_ast(ctx.primitiveCall())

        if class_name == "PrimitiveCallContext":
            prim_name = ctx.primitive().getText() if ctx.primitive() else "fold_hood"
            args = [self._ctx_to_ast(e) for e in ctx.expr()]
            return AstNode(node_type="call", name=prim_name, children=args)

        if class_name == "FuncCallContext":
            return self._ctx_to_ast(ctx.functionCall())

        if class_name == "FunctionCallContext":
            name = ctx.NAME().getText()
            args = [self._ctx_to_ast(e) for e in ctx.argList().expr()] if ctx.argList() else []
            return AstNode(node_type="call", name=name, children=args)

        if class_name == "ParenExprContext":
            return self._ctx_to_ast(ctx.expr())

        if class_name == "IntLiteralContext":
            return AstNode(node_type="int", value=int(ctx.INT_LIT().getText()))

        if class_name == "FloatLiteralContext":
            return AstNode(node_type="float", value=float(ctx.FLOAT_LIT().getText()))

        if class_name == "StringLiteralContext":
            text = ctx.STRING_LIT().getText()
            return AstNode(node_type="string", value=text.strip("'\""))

        if class_name == "NameRefContext":
            return AstNode(node_type="name", value=ctx.NAME().getText())

        # Generic fallback: recurse into children
        children = []
        for i in range(ctx.getChildCount()):
            child = ctx.getChild(i)
            if isinstance(child, antlr4.ParserRuleContext):
                children.append(self._ctx_to_ast(child))
        return AstNode(node_type=class_name.replace("Context", "").lower(), children=children)


def ast_to_dsl(ast: AstNode) -> Dict[str, Any]:
    """
    Convert parsed AST to Python DSL representation.

    Phase 5: Simplified version; full implementation in Phase 6
    """
    if ast.node_type == "program":
        programs = []
        for func_node in ast.children:
            programs.append(ast_to_dsl(func_node))
        return {"type": "program", "functions": programs}

    elif ast.node_type == "function":
        initial_state_node = ast.children[0]
        compute_node = ast.children[1]

        return {
            "type": "function",
            "name": ast.name,
            "initial_state": ast_to_dsl(initial_state_node),
            "compute": ast_to_dsl(compute_node),
        }

    elif ast.node_type == "binop":
        return {
            "type": "binop",
            "op": ast.value,
            "left": ast_to_dsl(ast.children[0]),
            "right": ast_to_dsl(ast.children[1]),
        }

    elif ast.node_type == "call":
        return {
            "type": "call",
            "name": ast.name,
            "arg": ast_to_dsl(ast.children[0]) if ast.children else None,
        }

    elif ast.node_type in ("int", "float", "name", "string"):
        return {"type": ast.node_type, "value": ast.value}

    else:
        # Recursively convert children
        children_dsl = [ast_to_dsl(child) for child in ast.children]
        return {
            "type": ast.node_type,
            "children": children_dsl,
        }
