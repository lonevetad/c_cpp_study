import os
from pathlib import Path
from typing import List, Optional


class CmakeGenerator:
    """Generate CMakeLists.txt for compiled FCPP programs."""

    def __init__(
        self,
        fcpp_src_path: Optional[Path] = None,
        runtime_include_path: Optional[Path] = None,
    ):
        if fcpp_src_path is not None:
            self.fcpp_src_path = fcpp_src_path
        else:
            env = os.environ.get("FCPP_INCLUDE_PATH")
            self.fcpp_src_path = Path(env) if env else None
        self.runtime_include_path = runtime_include_path

    def generate(
        self,
        program_name: str,
        cpp_file: Path,
        output_dir: Optional[Path] = None,
    ) -> str:
        """Return CMakeLists.txt content as a string."""
        output_dir_line = ""
        if output_dir:
            output_dir_line = (
                f"set(CMAKE_RUNTIME_OUTPUT_DIRECTORY {output_dir})\n"
            )

        include_lines = ""
        if self.fcpp_src_path:
            include_lines += f"include_directories({self.fcpp_src_path})\n"
        if self.runtime_include_path:
            include_lines += f"include_directories({self.runtime_include_path})\n"

        return (
            "cmake_minimum_required(VERSION 3.14)\n"
            f"project({program_name})\n\n"
            "set(CMAKE_CXX_STANDARD 14)\n"
            "set(CMAKE_CXX_STANDARD_REQUIRED ON)\n\n"
            f"{output_dir_line}"
            f"{include_lines}\n"
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
        """Return the shell commands needed to configure and build."""
        return [
            f"cmake -S {cmake_dir} -B {build_dir} -DCMAKE_BUILD_TYPE=Release",
            f"cmake --build {build_dir} --parallel",
        ]
