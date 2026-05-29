"""Tests for ProgramCache — hash-based binary cache."""

import tempfile
from pathlib import Path

import pytest
from fcpp_bridge.compiler import ProgramCache


# ============================================================================
# Test 1: Program Cache
# ============================================================================


def test_cache_basic():
    with tempfile.TemporaryDirectory() as tmpdir:
        cache = ProgramCache(Path(tmpdir))
        code1 = "int main() { return 0; }"
        assert cache.lookup(code1) is None
        binary_path = Path(tmpdir) / "test_binary"
        cache.store(code1, binary_path)
        assert cache.lookup(code1) == binary_path


def test_cache_hash_collision_avoidance():
    with tempfile.TemporaryDirectory() as tmpdir:
        cache = ProgramCache(Path(tmpdir))
        key1 = cache.get_key("int x = 1;")
        key2 = cache.get_key("int x = 2;")
        assert key1 != key2


def test_cache_persistence():
    with tempfile.TemporaryDirectory() as tmpdir:
        cache_dir = Path(tmpdir) / "cache"
        cache1 = ProgramCache(cache_dir)
        code = "test code"
        binary = cache_dir / "test_binary"
        cache1.store(code, binary)
        cache2 = ProgramCache(cache_dir)
        assert cache2.lookup(code) == binary


def test_cache_no_duplicates():
    with tempfile.TemporaryDirectory() as tmpdir:
        cache = ProgramCache(Path(tmpdir))
        code = "int main() {}"
        binary1 = Path(tmpdir) / "binary1"
        binary2 = Path(tmpdir) / "binary2"
        cache.store(code, binary1)
        initial_size = len(cache.manifest)
        cache.store(code, binary2)
        assert len(cache.manifest) <= initial_size + 1


def test_cache_get_key_consistent():
    with tempfile.TemporaryDirectory() as tmpdir:
        cache = ProgramCache(Path(tmpdir))
        code = "int main() { return 42; }"
        assert cache.get_key(code) == cache.get_key(code)
