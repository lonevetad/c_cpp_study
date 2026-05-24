from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class CompilationResult:
    """Result of compilation attempt."""

    success: bool
    binary_path: Optional[Path]
    stderr: str
    stdout: str
    compile_time_seconds: float
