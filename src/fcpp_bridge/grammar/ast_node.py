from dataclasses import dataclass
from typing import Any, List, Optional


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
