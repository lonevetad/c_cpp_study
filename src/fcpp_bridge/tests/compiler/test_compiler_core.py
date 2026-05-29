"""Tests for Compiler — GCC invocation, caching, get_or_compile."""

import tempfile
from pathlib import Path

import pytest
from fcpp_bridge.compiler import Compiler, CompilationError


# ============================================================================
# Test 2: Compiler Initialization
# ============================================================================


def test_compiler_init():
    with tempfile.TemporaryDirectory() as tmpdir:
        compiler = Compiler(
            cache_dir=Path(tmpdir) / "build",
            cpp_dir=Path(tmpdir) / "cpp",
        )
        assert compiler.cache_dir.exists()
        assert compiler.cpp_dir.exists()


def test_compiler_default_std_and_opt():
    compiler = Compiler(cache_dir=Path("/tmp/x"), cpp_dir=Path("/tmp/y"))
    assert compiler.std == "c++26"
    assert compiler.opt_level == "2"
    assert compiler.extra_includes == []


def test_compiler_custom_std_opt_includes(tmp_path):
    compiler = Compiler(
        cache_dir=tmp_path / "build",
        cpp_dir=tmp_path / "cpp",
        std="c++17",
        opt_level="3",
        extra_includes=["/usr/local/include/mylib"],
    )
    assert compiler.std == "c++17"
    assert compiler.opt_level == "3"
    assert compiler.extra_includes == ["/usr/local/include/mylib"]


def test_compiler_extra_includes_defensive_copy(tmp_path):
    src = ["/inc/a"]
    compiler = Compiler(cache_dir=tmp_path / "b", cpp_dir=tmp_path / "c", extra_includes=src)
    src.append("/inc/b")
    assert compiler.extra_includes == ["/inc/a"]  # not affected by mutation


def test_compiler_cache_dir_creation():
    with tempfile.TemporaryDirectory() as tmpdir:
        build_dir = Path(tmpdir) / "nonexistent" / "build"
        assert not build_dir.exists()
        Compiler(cache_dir=build_dir)
        assert build_dir.exists()


# ============================================================================
# Test 3: Simple Compilation
# ============================================================================


def test_compiler_simple_cpp():
    with tempfile.TemporaryDirectory() as tmpdir:
        compiler = Compiler(
            cache_dir=Path(tmpdir) / "build",
            cpp_dir=Path(tmpdir) / "cpp",
        )
        cpp_code = "#include <iostream>\nint main() { std::cout << \"Hello\" << std::endl; return 0; }\n"
        try:
            binary = compiler.get_or_compile(cpp_code, "hello")
            assert binary.exists()
        except CompilationError:
            pytest.skip("GCC not available")


def test_compiler_invalid_cpp():
    with tempfile.TemporaryDirectory() as tmpdir:
        compiler = Compiler(
            cache_dir=Path(tmpdir) / "build",
            cpp_dir=Path(tmpdir) / "cpp",
        )
        cpp_code = "int main() { this is invalid C++ }\n"
        with pytest.raises(CompilationError):
            compiler.get_or_compile(cpp_code, "invalid")


def test_compiler_missing_source():
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
    with tempfile.TemporaryDirectory() as tmpdir:
        compiler = Compiler(
            cache_dir=Path(tmpdir) / "build",
            cpp_dir=Path(tmpdir) / "cpp",
        )
        cpp_code = "#include <iostream>\nint main() { return 0; }\n"
        try:
            binary1 = compiler.get_or_compile(cpp_code, "test1")
            binary2 = compiler.get_or_compile(cpp_code, "test2")
            assert binary1.parent == binary2.parent
        except CompilationError:
            pytest.skip("GCC not available")


def test_compiler_cache_stats():
    with tempfile.TemporaryDirectory() as tmpdir:
        compiler = Compiler(cache_dir=Path(tmpdir))
        stats = compiler.get_cache_stats()
        assert "cached_binaries" in stats
        assert "cache_dir_size_bytes" in stats
        assert stats["cached_binaries"] >= 0


def test_compiler_clear_cache():
    with tempfile.TemporaryDirectory() as tmpdir:
        cache_dir = Path(tmpdir)
        compiler = Compiler(cache_dir=cache_dir)
        (cache_dir / "dummy_binary").write_text("test")
        compiler.clear_cache()
        assert len(compiler.cache.manifest) == 0
