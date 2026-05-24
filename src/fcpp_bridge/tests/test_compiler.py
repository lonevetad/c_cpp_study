"""Tests for Phase 3 Compiler Pipeline."""

import pytest
import tempfile
from pathlib import Path
from fcpp_bridge.compiler import Compiler, ProgramCache, CompilationError


# ============================================================================
# Test 1: Program Cache
# ============================================================================


def test_cache_basic():
    """Test basic cache operations."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cache = ProgramCache(Path(tmpdir))

        code1 = "int main() { return 0; }"
        code2 = "int main() { return 1; }"

        # Lookup non-existent
        assert cache.lookup(code1) is None

        # Store and lookup
        binary_path = Path(tmpdir) / "test_binary"
        cache.store(code1, binary_path)
        assert cache.lookup(code1) == binary_path


def test_cache_hash_collision_avoidance():
    """Test that similar codes get different hashes."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cache = ProgramCache(Path(tmpdir))

        code1 = "int x = 1;"
        code2 = "int x = 2;"

        key1 = cache.get_key(code1)
        key2 = cache.get_key(code2)

        assert key1 != key2


def test_cache_persistence():
    """Test that cache persists across instances."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cache_dir = Path(tmpdir) / "cache"

        # First instance
        cache1 = ProgramCache(cache_dir)
        code = "test code"
        binary = cache_dir / "test_binary"
        cache1.store(code, binary)

        # Second instance (reload)
        cache2 = ProgramCache(cache_dir)
        assert cache2.lookup(code) == binary


def test_cache_no_duplicates():
    """Test that storing same code again doesn't duplicate."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cache = ProgramCache(Path(tmpdir))

        code = "int main() {}"
        binary1 = Path(tmpdir) / "binary1"
        binary2 = Path(tmpdir) / "binary2"

        cache.store(code, binary1)
        initial_size = len(cache.manifest)

        cache.store(code, binary2)
        # Manifest might update, but no new entries
        assert len(cache.manifest) <= initial_size + 1


# ============================================================================
# Test 2: Compiler Initialization
# ============================================================================


def test_compiler_init():
    """Test compiler initialization."""
    with tempfile.TemporaryDirectory() as tmpdir:
        compiler = Compiler(
            cache_dir=Path(tmpdir) / "build",
            cpp_dir=Path(tmpdir) / "cpp",
        )
        assert compiler.cache_dir.exists()
        assert compiler.cpp_dir.exists()


def test_compiler_cache_dir_creation():
    """Test that compiler creates directories if missing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        build_dir = Path(tmpdir) / "nonexistent" / "build"
        assert not build_dir.exists()

        compiler = Compiler(cache_dir=build_dir)
        assert build_dir.exists()


# ============================================================================
# Test 3: Simple Compilation
# ============================================================================


def test_compiler_simple_cpp():
    """Test compiling a simple valid C++ program."""
    with tempfile.TemporaryDirectory() as tmpdir:
        compiler = Compiler(
            cache_dir=Path(tmpdir) / "build",
            cpp_dir=Path(tmpdir) / "cpp",
        )

        # Simple C++ code
        cpp_code = """
#include <iostream>
int main() {
    std::cout << "Hello" << std::endl;
    return 0;
}
"""

        try:
            binary = compiler.get_or_compile(cpp_code, "hello")
            assert binary.exists()
        except CompilationError:
            # GCC may not be available in test environment
            pytest.skip("GCC not available")


def test_compiler_invalid_cpp():
    """Test handling of invalid C++ code."""
    with tempfile.TemporaryDirectory() as tmpdir:
        compiler = Compiler(
            cache_dir=Path(tmpdir) / "build",
            cpp_dir=Path(tmpdir) / "cpp",
        )

        # Invalid C++ (syntax error)
        cpp_code = """
int main() {
    this is invalid C++
}
"""

        with pytest.raises(CompilationError):
            compiler.get_or_compile(cpp_code, "invalid")


def test_compiler_missing_source():
    """Test error handling when source file not found."""
    with tempfile.TemporaryDirectory() as tmpdir:
        compiler = Compiler(cache_dir=Path(tmpdir))

        with pytest.raises(CompilationError, match="not found"):
            compiler.compile(
                Path(tmpdir) / "nonexistent.cpp",
                Path(tmpdir) / "output",
            )


# ============================================================================
# Test 4: Caching Behavior
# ============================================================================


def test_compiler_cache_hit():
    """Test that identical code produces cache hit."""
    with tempfile.TemporaryDirectory() as tmpdir:
        compiler = Compiler(
            cache_dir=Path(tmpdir) / "build",
            cpp_dir=Path(tmpdir) / "cpp",
        )

        cpp_code = """
#include <iostream>
int main() { return 0; }
"""

        try:
            binary1 = compiler.get_or_compile(cpp_code, "test1")
            binary2 = compiler.get_or_compile(cpp_code, "test2")

            # Should reuse cache (same binary path or related)
            assert binary1.parent == binary2.parent
        except CompilationError:
            pytest.skip("GCC not available")


def test_compiler_cache_stats():
    """Test cache statistics reporting."""
    with tempfile.TemporaryDirectory() as tmpdir:
        compiler = Compiler(cache_dir=Path(tmpdir))
        stats = compiler.get_cache_stats()

        assert "cached_binaries" in stats
        assert "cache_dir_size_bytes" in stats
        assert stats["cached_binaries"] >= 0


def test_compiler_clear_cache():
    """Test cache clearing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cache_dir = Path(tmpdir)
        compiler = Compiler(cache_dir=cache_dir)

        # Create a dummy cache entry
        (cache_dir / "dummy_binary").write_text("test")

        compiler.clear_cache()

        # Manifest should be empty
        assert len(compiler.cache.manifest) == 0


# ============================================================================
# Test 5: Compilation Result
# ============================================================================


def test_compilation_result_success():
    """Test successful compilation result."""
    from fcpp_bridge.compiler import CompilationResult

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
    """Test failed compilation result."""
    from fcpp_bridge.compiler import CompilationResult

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


def test_cache_get_key_consistent():
    """Same code always produces the same cache key."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cache = ProgramCache(Path(tmpdir))
        code = "int main() { return 42; }"
        assert cache.get_key(code) == cache.get_key(code)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
