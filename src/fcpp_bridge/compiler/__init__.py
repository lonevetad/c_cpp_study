"""Compilation pipeline — build C++ code to executable."""

import hashlib
import platform
import re
import shutil
import subprocess
import os
from pathlib import Path
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass, field


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
        """Return cached binary path (None if not in manifest).

        Does NOT check file existence — that is the caller's responsibility,
        because the cache is a content-addressed store and shouldn't recompile
        just because a binary was moved.
        """
        cache_key = self._hash(cpp_code)
        return self.manifest.get(cache_key)

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
            "-O2",
            "-I", str(Path(__file__).parent.parent / "fcpp_clone_GITIGNORE_ME" / "src"),
        ]

        # LLD linker: required on Windows (BFD ld crashes on large fcpp COMDAT tables).
        # Use it on Linux when available.  Skip on macOS — Apple ld64 doesn't support it.
        _sys = platform.system()
        if _sys == "Windows" or (_sys == "Linux" and shutil.which("lld") is not None):
            flags.append("-fuse-ld=lld")

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
        # Check cache first; recompile if cached path no longer exists on disk.
        cached = self.cache.lookup(cpp_code)
        if cached and cached.exists():
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


# =============================================================================
# CMakeLists.txt Generator (Phase 3)
# =============================================================================


class CmakeGenerator:
    """Generate CMakeLists.txt for compiled FCPP programs.

    Produces a CMakeLists.txt that compiles a single generated C++ source
    against the FCPP headers with the correct C++14 standard.
    """

    def __init__(
        self,
        fcpp_src_path: Optional[Path] = None,
        runtime_include_path: Optional[Path] = None,
    ):
        """
        Args:
            fcpp_src_path: Path to the FCPP source tree (contains ``src/``).
                           Defaults to the sibling ``fcpp_clone_GITIGNORE_ME/fcpp``
                           inside the project.
            runtime_include_path: Path to the generated runtime headers
                                  (ipc_server.hpp, etc.).  Defaults to
                                  ``<project>/build/runtime``.
        """
        project_root = Path(__file__).parent.parent
        self.fcpp_src_path = fcpp_src_path or (
            project_root / "fcpp_clone_GITIGNORE_ME" / "fcpp" / "src"
        )
        self.runtime_include_path = runtime_include_path or (
            project_root / "build" / "runtime"
        )

    def generate(
        self,
        program_name: str,
        cpp_file: Path,
        output_dir: Optional[Path] = None,
    ) -> str:
        """Return CMakeLists.txt content as a string.

        Args:
            program_name: Target executable name (no spaces).
            cpp_file: Path to the ``.cpp`` source file to compile.
            output_dir: Where the binary should land (CMAKE_RUNTIME_OUTPUT_DIRECTORY).
        """
        output_dir_line = ""
        if output_dir:
            output_dir_line = (
                f"set(CMAKE_RUNTIME_OUTPUT_DIRECTORY {output_dir})\n"
            )

        return (
            "cmake_minimum_required(VERSION 3.14)\n"
            f"project({program_name})\n\n"
            "set(CMAKE_CXX_STANDARD 14)\n"
            "set(CMAKE_CXX_STANDARD_REQUIRED ON)\n\n"
            f"{output_dir_line}"
            f"include_directories({self.fcpp_src_path})\n"
            f"include_directories({self.runtime_include_path})\n\n"
            f"add_executable({program_name} {cpp_file.name})\n\n"
            f"target_compile_options({program_name} PRIVATE\n"
            "    -Wall -Wextra -O2\n"
            ")\n"
        )

    def write(
        self,
        program_name: str,
        cpp_file: Path,
        output_dir: Optional[Path] = None,
    ) -> Path:
        """Write CMakeLists.txt next to *cpp_file* and return its path."""
        cmake_path = cpp_file.parent / "CMakeLists.txt"
        cmake_path.write_text(
            self.generate(program_name, cpp_file, output_dir)
        )
        return cmake_path

    def generate_build_commands(
        self,
        cmake_dir: Path,
        build_dir: Path,
    ) -> List[str]:
        """Return the shell commands needed to configure and build.

        Returns a list of commands that can be joined with ``&&`` or run
        individually in a subprocess.
        """
        return [
            f"cmake -S {cmake_dir} -B {build_dir} -DCMAKE_BUILD_TYPE=Release",
            f"cmake --build {build_dir} --parallel",
        ]


# =============================================================================
# GCC Error Parser (Phase 3)
# =============================================================================


@dataclass
class CompilationDiagnostic:
    """A single GCC/Clang diagnostic (error, warning, or note)."""

    file: str
    line: int
    column: int
    level: str   # "error", "warning", or "note"
    message: str
    context_line: str = ""  # the source line from the file (if available)

    def __str__(self) -> str:
        loc = f"{self.file}:{self.line}:{self.column}"
        return f"{loc}: {self.level}: {self.message}"


class CompilationErrorParser:
    """Parse GCC/Clang stderr and produce structured diagnostics.

    Maps compiler errors back to readable messages that surface the root
    cause without raw template noise.
    """

    # Standard GCC/Clang diagnostic line:
    #   path/to/file.cpp:42:10: error: 'x' was not declared
    _DIAG_RE = re.compile(
        r"^(?P<file>[^:]+):(?P<line>\d+):(?P<col>\d+):"
        r"\s*(?P<level>error|warning|note):\s*(?P<msg>.+)$"
    )

    # Template instantiation noise — lines to skip
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

            # Skip template instantiation noise
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
