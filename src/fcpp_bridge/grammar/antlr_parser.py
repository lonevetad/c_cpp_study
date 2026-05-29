from pathlib import Path
from typing import Any

from .ast_node import AstNode
from .parser_error import ParserError
from .aggregate_language_parser import AggregateLanguageParser


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
        """Parse aggregate program from string."""
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

        children = []
        for i in range(ctx.getChildCount()):
            child = ctx.getChild(i)
            if isinstance(child, antlr4.ParserRuleContext):
                children.append(self._ctx_to_ast(child))
        return AstNode(node_type=class_name.replace("Context", "").lower(), children=children)
