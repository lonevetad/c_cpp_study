"""Tests for CompilationResult dataclass."""

from pathlib import Path

import pytest
from fcpp_bridge.compiler import CompilationResult


# ============================================================================
# Test 5: Compilation Result
# ============================================================================


def test_compilation_result_success():
    result = CompilationResult(
        success=True,
        binary_path=Path("/tmp/test"),
        stderr="",
        stdout="",
        compile_time_seconds=1.5,
    )
    assert result.success
    assert result.binary_path == Path("/tmp/test")


def test_compilation_result_failure():
    result = CompilationResult(
        success=False,
        binary_path=None,
        stderr="error: undefined reference to main",
        stdout="",
        compile_time_seconds=0.5,
    )
    assert not result.success
    assert result.binary_path is None
    assert "undefined reference" in result.stderr
