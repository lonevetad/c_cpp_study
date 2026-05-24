import platform
import shutil
import subprocess
import time
from pathlib import Path
from typing import Dict, List, Optional

from .compilation_error import CompilationError
from .compilation_result import CompilationResult
from .program_cache import ProgramCache


class Compiler:
    """Invoke GCC to compile C++ code."""

    def __init__(
        self,
        cache_dir: Path = Path("build"),
        cpp_dir: Path = Path("cpp_transpiled"),
        gcc_path: str = "g++",
    ):
        self.cache_dir = cache_dir
        self.cpp_dir = cpp_dir
        self.gcc_path = gcc_path

        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cpp_dir.mkdir(parents=True, exist_ok=True)
        self.cache = ProgramCache(cache_dir)

    def compile(
        self,
        cpp_file: Path,
        output_binary: Path,
        extra_flags: List[str] = None,
    ) -> CompilationResult:
        """Compile C++ file to executable."""
        if not cpp_file.exists():
            raise CompilationError(f"C++ source not found: {cpp_file}")

        start = time.time()

        flags = [
            "-std=c++26",
            "-Wall",
            "-Wextra",
            "-O2",
            "-I", str(Path(__file__).parent.parent / "fcpp_clone_GITIGNORE_ME" / "src"),
        ]

        _sys = platform.system()
        if _sys == "Windows" or (_sys == "Linux" and shutil.which("lld") is not None):
            flags.append("-fuse-ld=lld")

        if extra_flags:
            flags.extend(extra_flags)

        cmd = [
            self.gcc_path,
            *flags,
            str(cpp_file),
            "-o", str(output_binary),
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120,
            )

            elapsed = time.time() - start

            if result.returncode != 0:
                return CompilationResult(
                    success=False,
                    binary_path=None,
                    stderr=result.stderr,
                    stdout=result.stdout,
                    compile_time_seconds=elapsed,
                )

            if not output_binary.exists():
                return CompilationResult(
                    success=False,
                    binary_path=None,
                    stderr="Binary not created",
                    stdout=result.stdout,
                    compile_time_seconds=elapsed,
                )

            return CompilationResult(
                success=True,
                binary_path=output_binary,
                stderr=result.stderr,
                stdout=result.stdout,
                compile_time_seconds=elapsed,
            )

        except subprocess.TimeoutExpired:
            return CompilationResult(
                success=False,
                binary_path=None,
                stderr="Compilation timeout (>120s)",
                stdout="",
                compile_time_seconds=120.0,
            )
        except Exception as e:
            return CompilationResult(
                success=False,
                binary_path=None,
                stderr=str(e),
                stdout="",
                compile_time_seconds=0.0,
            )

    def get_or_compile(self, cpp_code: str, program_name: str = "program") -> Path:
        """Get cached binary, or compile if not cached."""
        cached = self.cache.lookup(cpp_code)
        if cached and cached.exists():
            print(f"[Compiler] Cache hit: {cached}")
            return cached

        cache_key = self.cache.get_key(cpp_code)
        cpp_file = self.cpp_dir / f"{program_name}_{cache_key}.cpp"
        binary_path = self.cache_dir / f"{program_name}_{cache_key}"

        cpp_file.write_text(cpp_code)
        print(f"[Compiler] Generated: {cpp_file}")

        print(f"[Compiler] Compiling {cpp_file}...")
        result = self.compile(cpp_file, binary_path)

        if not result.success:
            print(f"[Compiler] Compilation failed:")
            if result.stderr:
                print(f"  stderr: {result.stderr[:500]}")
            if result.stdout:
                print(f"  stdout: {result.stdout[:500]}")
            raise CompilationError(
                f"Compilation failed: {result.stderr or result.stdout}"
            )

        print(f"[Compiler] Success: {binary_path} ({result.compile_time_seconds:.2f}s)")

        self.cache.store(cpp_code, binary_path)

        return binary_path

    def clear_cache(self) -> None:
        """Clear all cached binaries."""
        for f in self.cache_dir.glob("*"):
            if f.is_file() and f.name != ".cache_manifest":
                f.unlink()
        self.cache.manifest.clear()
        self.cache._save_manifest()
        print("[Compiler] Cache cleared")

    def get_cache_stats(self) -> Dict[str, int]:
        """Get cache statistics."""
        return {
            "cached_binaries": len(self.cache.manifest),
            "cache_dir_size_bytes": sum(
                f.stat().st_size for f in self.cache_dir.glob("*") if f.is_file()
            ),
        }
