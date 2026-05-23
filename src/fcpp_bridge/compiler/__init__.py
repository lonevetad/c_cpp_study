"""Compilation pipeline — build C++ code to executable."""

import hashlib
import subprocess
import os
from pathlib import Path
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass


class CompilationError(Exception):
    """Raised when compilation fails."""

    pass


@dataclass
class CompilationResult:
    """Result of compilation attempt."""

    success: bool
    binary_path: Optional[Path]
    stderr: str
    stdout: str
    compile_time_seconds: float


class ProgramCache:
    """Cache compiled programs by content hash."""

    def __init__(self, cache_dir: Path):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.manifest: Dict[str, Path] = self._load_manifest()

    def _load_manifest(self) -> Dict[str, Path]:
        """Load cache manifest from disk."""
        manifest_path = self.cache_dir / ".cache_manifest"
        manifest = {}
        if manifest_path.exists():
            for line in manifest_path.read_text().strip().split("\n"):
                if line and ":" in line:
                    key, path = line.split(":", 1)
                    manifest[key] = Path(path)
        return manifest

    def _save_manifest(self) -> None:
        """Save cache manifest to disk."""
        manifest_path = self.cache_dir / ".cache_manifest"
        lines = [f"{k}:{v}" for k, v in self.manifest.items()]
        manifest_path.write_text("\n".join(lines))

    def _hash(self, content: str) -> str:
        """Hash C++ code to generate unique ID."""
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def lookup(self, cpp_code: str) -> Optional[Path]:
        """Return cached binary path if exists."""
        cache_key = self._hash(cpp_code)
        if cache_key in self.manifest:
            binary_path = self.manifest[cache_key]
            if binary_path.exists():
                return binary_path
        return None

    def store(self, cpp_code: str, binary_path: Path) -> None:
        """Cache binary path for this code."""
        cache_key = self._hash(cpp_code)
        self.manifest[cache_key] = binary_path
        self._save_manifest()

    def get_key(self, cpp_code: str) -> str:
        """Get cache key for code (for filename generation)."""
        return self._hash(cpp_code)


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
        """
        Compile C++ file to executable.

        Args:
            cpp_file: Path to .cpp source
            output_binary: Path to output executable
            extra_flags: Additional GCC flags (e.g., ["-O3", "-g"])

        Returns:
            CompilationResult with success status and logs
        """
        if not cpp_file.exists():
            raise CompilationError(f"C++ source not found: {cpp_file}")

        import time
        start = time.time()

        # Base flags
        flags = [
            "-std=c++26",
            "-Wall",
            "-Wextra",
            "-fuse-ld=lld",  # LLD linker (required for Windows)
            "-O2",  # Optimization level
            "-I", str(Path(__file__).parent.parent / "fcpp_clone_GITIGNORE_ME" / "src"),
        ]

        if extra_flags:
            flags.extend(extra_flags)

        # Build command
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
                timeout=120,  # 2 minute timeout
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
        """
        Get cached binary, or compile if not cached.

        Args:
            cpp_code: C++ source code as string
            program_name: Base name for program (for identification)

        Returns:
            Path to executable binary

        Raises:
            CompilationError: if compilation fails
        """
        # Check cache first
        cached = self.cache.lookup(cpp_code)
        if cached:
            print(f"[Compiler] Cache hit: {cached}")
            return cached

        # Generate filenames
        cache_key = self.cache.get_key(cpp_code)
        cpp_file = self.cpp_dir / f"{program_name}_{cache_key}.cpp"
        binary_path = self.cache_dir / f"{program_name}_{cache_key}"

        # Write C++ source
        cpp_file.write_text(cpp_code)
        print(f"[Compiler] Generated: {cpp_file}")

        # Compile
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

        # Cache the result
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
