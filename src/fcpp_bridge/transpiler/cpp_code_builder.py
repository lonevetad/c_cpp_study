from typing import List


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

        for inc in self.includes:
            lines.append(f"#include {inc}")

        if self.includes:
            lines.append("")

        for decl in self.declarations:
            lines.append(decl)
            lines.append("")

        for helper in self.helpers:
            lines.append(helper)
            lines.append("")

        if self.main_aggregate:
            lines.append(self.main_aggregate)

        return "\n".join(lines)
