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
            (r"\b(nbr|old|max_hood|min_hood|fold_hood|count_hood)\b", "PRIMITIVE"),
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

    def _parse_call_expr(self) -> AstNode:
        """Parse: NAME ( args ) | atom"""
        if self._current_token() in ("nbr", "old", "max_hood", "min_hood", "fold_hood"):
            primitive = self._consume()
            self._consume("(")
            arg = self._parse_expr()
            self._consume(")")

            return AstNode(
                node_type="call",
                name=primitive,
                children=[arg],
            )

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
