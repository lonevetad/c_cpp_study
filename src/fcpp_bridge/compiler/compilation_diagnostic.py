from dataclasses import dataclass, field


@dataclass
class CompilationDiagnostic:
    """A single GCC/Clang diagnostic (error, warning, or note)."""

    file: str
    line: int
    column: int
    level: str   # "error", "warning", or "note"
    message: str
    context_line: str = ""

    def __str__(self) -> str:
        loc = f"{self.file}:{self.line}:{self.column}"
        return f"{loc}: {self.level}: {self.message}"
