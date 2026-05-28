#!/usr/bin/env python3
"""
generate_antlr.py — Generate ANTLR4 Python3 parser stubs from AggregateProgram.g4.

Usage
-----
    python3 generate_antlr.py [--download] [--antlr-jar PATH] [--output-dir DIR]

What it does
------------
1. Checks that Java 11+ is in PATH.
2. Locates (or downloads) the ANTLR 4.13.1 complete jar.
3. Runs ANTLR to generate Python3 lexer/parser/listener/visitor stubs.
4. Writes an ``__init__.py`` into the output directory.

Output directory
----------------
Default: ``<this-script-dir>/__antlr_gen/``

The generated files are::

    __antlr_gen/
    ├── __init__.py
    ├── AggregateProgramLexer.py
    ├── AggregateProgramParser.py
    ├── AggregateProgramListener.py
    └── AggregateProgramVisitor.py

After generation
----------------
Install the Python runtime (once, in the project venv)::

    pip install antlr4-python3-runtime==4.13.1

Then verify the integration::

    python3 -c "
    from fcpp_bridge.grammar import AntlrParser
    p = AntlrParser()
    print('ANTLR active:', p._antlr_available)
    "

Note
----
``__antlr_gen/`` is git-ignored (generated code). Re-run this script after
any grammar change.
"""

import argparse
import logging
import shutil
import subprocess
import sys
from pathlib import Path

from fcpp_bridge.log import configure_bridge_logging, get_logger

_log = get_logger(__name__)

ANTLR_VERSION = "4.13.1"
ANTLR_JAR_NAME = f"antlr-{ANTLR_VERSION}-complete.jar"
ANTLR_DOWNLOAD_URL = f"https://www.antlr.org/download/{ANTLR_JAR_NAME}"

_HERE = Path(__file__).parent.resolve()
GRAMMAR_FILE = _HERE / "AggregateProgram.g4"
DEFAULT_JAR = _HERE / ANTLR_JAR_NAME
DEFAULT_OUTPUT = _HERE / "__antlr_gen"

_INIT_CONTENT = (
    "# Auto-generated ANTLR4 Python3 stubs — do not edit.\n"
    "# Re-generate with: python3 grammar/generate_antlr.py --download\n"
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _check_java() -> None:
    if shutil.which("java") is None:
        _die(
            "Java not found in PATH. Install Java 11+ and try again.\n"
            "  Ubuntu/Debian: sudo apt install default-jdk\n"
            "  macOS:         brew install openjdk"
        )


def _download_jar(target: Path) -> None:
    import urllib.request

    _log.info("Downloading %s …", ANTLR_JAR_NAME)
    try:
        urllib.request.urlretrieve(ANTLR_DOWNLOAD_URL, target)
    except Exception as exc:
        _die(f"Download failed: {exc}\nManually download from {ANTLR_DOWNLOAD_URL}")
    _log.info("Saved to %s", target)


def _run_antlr(jar: Path, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        "java", "-jar", str(jar),
        "-Dlanguage=Python3",
        "-visitor",
        "-listener",
        "-o", str(output_dir),
        str(GRAMMAR_FILE),
    ]
    _log.info("Running: %s", " ".join(cmd))
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)
    if result.returncode != 0:
        _die(f"ANTLR exited with code {result.returncode}")


def _die(msg: str) -> None:
    _log.error("%s", msg)
    sys.exit(1)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    configure_bridge_logging(level=logging.INFO, stream=sys.stdout)
    parser = argparse.ArgumentParser(
        prog="generate_antlr.py",
        description="Generate ANTLR4 Python3 parser stubs from AggregateProgram.g4",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--antlr-jar",
        default=str(DEFAULT_JAR),
        metavar="PATH",
        help=f"Path to ANTLR {ANTLR_VERSION} complete jar (default: {DEFAULT_JAR})",
    )
    parser.add_argument(
        "--download",
        action="store_true",
        help="Download the jar if not already present at --antlr-jar path",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT),
        metavar="DIR",
        help=f"Output directory for stubs (default: {DEFAULT_OUTPUT})",
    )
    args = parser.parse_args()

    jar = Path(args.antlr_jar)
    out_dir = Path(args.output_dir)

    _check_java()

    if not jar.exists():
        if args.download:
            _download_jar(jar)
        else:
            _die(
                f"ANTLR jar not found at {jar}.\n"
                f"  Run with --download to fetch it automatically.\n"
                f"  Or: python3 generate_antlr.py --download"
            )

    _run_antlr(jar, out_dir)

    # Ensure the output directory is importable as a Python package.
    init_file = out_dir / "__init__.py"
    if not init_file.exists():
        init_file.write_text(_INIT_CONTENT)

    print(f"\nGenerated files in {out_dir}/:")
    for f in sorted(out_dir.glob("*.py")):
        print(f"  {f.name}")

    print(
        "\nNext steps:\n"
        f"  pip install antlr4-python3-runtime=={ANTLR_VERSION}\n"
        "\nVerify:\n"
        "  python3 -c \"\n"
        "  from fcpp_bridge.grammar import AntlrParser\n"
        "  p = AntlrParser()\n"
        "  print('ANTLR active:', p._antlr_available)\n"
        "  \""
    )


if __name__ == "__main__":
    main()
