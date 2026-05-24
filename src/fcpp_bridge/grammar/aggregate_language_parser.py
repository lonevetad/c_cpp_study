from pathlib import Path
from typing import Any, Dict, List, Optional

from .ast_node import AstNode
from .parser_error import ParserError


class AggregateLanguageParser:
    """Parse aggregate programs from strings or files."""

    def __init__(self):
        self.tokens: List[str] = []
        self.pos = 0

    def parse_string(self, program_str: str) -> AstNode:
        """Parse program from string."""
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

    def _tokenize(self, program_str: str) -> None:
        """Tokenize program string."""
        import re

        patterns = [
            (r"#.*$", "COMMENT"),
            (r"\s+", "WHITESPACE"),
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

    def _current_token(self) -> Optional[str]:
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return None

    def _peek_token(self, offset: int = 1) -> Optional[str]:
        if self.pos + offset < len(self.tokens):
            return self.tokens[self.pos + offset]
        return None

    def _consume(self, expected: Optional[str] = None) -> str:
        token = self._current_token()
        if expected and token != expected:
            raise ParserError(f"Expected '{expected}', got '{token}'")
        if token is None:
            raise ParserError("Unexpected end of input")
        self.pos += 1
        return token

    def _parse_program(self) -> AstNode:
        functions = []
        while self.pos < len(self.tokens):
            functions.append(self._parse_function())
        return AstNode(node_type="program", children=functions)

    def _parse_function(self) -> AstNode:
        self._consume("def")
        name = self._consume()
        self._consume(":")
        initial_state = self._parse_initial_state()
        compute = self._parse_compute()
        return AstNode(node_type="function", name=name, children=[initial_state, compute])

    def _parse_initial_state(self) -> AstNode:
        self._consume("initial_state")
        self._consume(":")
        expr = self._parse_expr()
        return AstNode(node_type="initial_state", children=[expr])

    def _parse_compute(self) -> AstNode:
        self._consume("compute")
        self._consume("(")
        self._consume()  # self_state
        self._consume(",")
        self._consume()  # neighbors
        self._consume(")")
        self._consume(":")
        expr = self._parse_expr()
        return AstNode(node_type="compute", children=[expr])

    def _parse_expr(self) -> AstNode:
        return self._parse_binary_expr()

    def _parse_binary_expr(self) -> AstNode:
        left = self._parse_call_expr()
        while self._current_token() in ("+", "-", "*", "/", "==", "!=", "<", ">"):
            op = self._consume()
            right = self._parse_call_expr()
            left = AstNode(node_type="binop", value=op, children=[left, right])
        return left

    _ALL_PRIMITIVES = frozenset({
        "nbr", "old", "nbr_uid", "oldnbr", "align", "align_inplace",
        "mod_other", "split", "fold_hood", "count_hood", "spawn",
        "min_hood", "max_hood", "sum_hood", "mean_hood",
        "all_hood", "any_hood", "list_hood",
        "abf_distance", "abf_hops", "bis_distance", "flex_distance",
        "broadcast", "bis_ksource_broadcast",
        "gossip", "gossip_min", "gossip_max", "gossip_mean",
        "sp_collection", "mp_collection", "wmp_collection",
        "list_idem_collection", "list_arith_collection",
        "follow_target", "follow_path", "follow_track",
        "random_rectangle_target", "rectangle_walk",
        "neighbour_elastic_force", "neighbour_gravitational_force", "neighbour_charged_force",
        "line_elastic_force", "plane_elastic_force",
        "point_elastic_force", "point_gravitational_force",
        "diameter_election", "diameter_election_distance",
        "color_election", "color_election_distance",
        "wave_election", "wave_election_distance",
        "constant", "constant_after", "counter", "delay",
        "round_since", "time_since", "timed_decay", "exponential_filter",
        "shared_clock", "shared_decay", "shared_filter",
        "toggle", "toggle_filter",
    })

    def _parse_call_expr(self) -> AstNode:
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
    """Convert parsed AST to Python DSL representation."""
    if ast.node_type == "program":
        return {"type": "program", "functions": [ast_to_dsl(f) for f in ast.children]}

    elif ast.node_type == "function":
        return {
            "type": "function",
            "name": ast.name,
            "initial_state": ast_to_dsl(ast.children[0]),
            "compute": ast_to_dsl(ast.children[1]),
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
        return {"type": ast.node_type, "children": [ast_to_dsl(c) for c in ast.children]}
