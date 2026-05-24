import re
from typing import List

from .compilation_error import CompilationError
from .compilation_diagnostic import CompilationDiagnostic


class CompilationErrorParser:
    """Parse GCC/Clang stderr and produce structured diagnostics."""

    _DIAG_RE = re.compile(
        r"^(?P<file>[^:]+):(?P<line>\d+):(?P<col>\d+):"
        r"\s*(?P<level>error|warning|note):\s*(?P<msg>.+)$"
    )

    _SKIP_PREFIXES = (
        "In file included from",
        "                 from",
        "In instantiation of",
        "required from",
        "required by",
    )

    @staticmethod
    def parse(stderr: str) -> List[CompilationDiagnostic]:
        """Parse GCC stderr into a list of CompilationDiagnostic objects."""
        diagnostics: List[CompilationDiagnostic] = []

        for raw_line in stderr.splitlines():
            line = raw_line.strip()

            if any(line.startswith(p) for p in CompilationErrorParser._SKIP_PREFIXES):
                continue

            m = CompilationErrorParser._DIAG_RE.match(line)
            if m:
                diagnostics.append(
                    CompilationDiagnostic(
                        file=m.group("file"),
                        line=int(m.group("line")),
                        column=int(m.group("col")),
                        level=m.group("level"),
                        message=m.group("msg").strip(),
                    )
                )

        return diagnostics

    @staticmethod
    def errors_only(
        diagnostics: List[CompilationDiagnostic],
    ) -> List[CompilationDiagnostic]:
        """Return only error-level diagnostics."""
        return [d for d in diagnostics if d.level == "error"]

    @staticmethod
    def format_summary(
        diagnostics: List[CompilationDiagnostic],
        max_errors: int = 5,
    ) -> str:
        """Format up to *max_errors* errors as a compact Python-style message."""
        errors = CompilationErrorParser.errors_only(diagnostics)
        if not errors:
            return "No errors found."

        lines = [f"{len(errors)} compilation error(s):"]
        for d in errors[:max_errors]:
            lines.append(f"  {d}")
        if len(errors) > max_errors:
            lines.append(f"  ... and {len(errors) - max_errors} more error(s)")
        return "\n".join(lines)

    @staticmethod
    def raise_if_errors(stderr: str) -> None:
        """Parse *stderr* and raise CompilationError if any errors found."""
        diags = CompilationErrorParser.parse(stderr)
        errors = CompilationErrorParser.errors_only(diags)
        if errors:
            summary = CompilationErrorParser.format_summary(diags)
            raise CompilationError(summary)
