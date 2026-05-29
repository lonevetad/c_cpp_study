"""FCPP Bridge — end-to-end example with per-step execution control.

Default (all steps):
    python end_to_end.py

Resume from a specific step (prior artifacts are loaded from disk):
    python end_to_end.py --from compile
    python end_to_end.py --from run

Run an explicit subset of steps:
    python end_to_end.py --steps validate transpile
    python end_to_end.py --steps compile run

Step names: validate  transpile  compile  run

Artifacts written to disk so later steps can be resumed independently:
    examples/.fcpp_cpp/consensus_latest.cpp   written by: transpile
    examples/.fcpp_build/.latest_binary       written by: compile  (stores path)
"""
import argparse
import sys
from pathlib import Path

from fcpp_bridge.python_dsl import aggregate_function, Neighborhood, AggregateValidator
from fcpp_bridge.transpiler import Transpiler
from fcpp_bridge.compiler import Compiler

# ── Artifact paths ────────────────────────────────────────────────────────────
_CPP_DIR    = Path(__file__).parent / ".fcpp_cpp"
_BUILD_DIR  = Path(__file__).parent / ".fcpp_build"
_CPP_LATEST = _CPP_DIR / "consensus_latest.cpp"
_BIN_LATEST = _BUILD_DIR / ".latest_binary"     # stores the binary path as text

STEPS = ["validate", "transpile", "compile", "run"]


# ── Aggregate function ────────────────────────────────────────────────────────

@aggregate_function
class ConsensusAggregate:
    """
    Byzantine Consensus: Nodes agree on maximum value seen.

    Theory: A simple form of Byzantine-resilient consensus where
    nodes propagate the maximum observed value, reaching consensus
    over multiple rounds.
    """

    def initial_state(self) -> float:
        import random
        return random.uniform(0.0, 100.0)

    def compute(self, self_state: float, neighbors: Neighborhood[float]) -> float:
        if not neighbors.values:
            return self_state
        return max(self_state, max(neighbors.values))


# ── Individual steps ──────────────────────────────────────────────────────────

def step_validate() -> bool:
    print("\n[validate] Validating Python DSL...")
    try:
        warnings = AggregateValidator.validate(ConsensusAggregate)
        print(f"    ✓ DSL valid  ({len(warnings)} warning(s))")
        for w in warnings:
            print(f"      - {w}")
        return True
    except Exception as exc:
        print(f"    ✗ {exc}")
        return False


def step_transpile() -> "str | None":
    """Transpile, save consensus_latest.cpp, return cpp_code or None on failure."""
    print("\n[transpile] Transpiling Python DSL → C++...")
    try:
        t = Transpiler(ConsensusAggregate)
        cpp = t.generate()
        _CPP_DIR.mkdir(parents=True, exist_ok=True)
        _CPP_LATEST.write_text(cpp)
        print(f"    ✓ Generated {len(cpp)} bytes  (state type: {t.get_state_type_cpp().name})")
        print(f"    ✓ Saved → {_CPP_LATEST}")
        return cpp
    except Exception as exc:
        print(f"    ✗ {exc}")
        return None


def step_compile(cpp_code: str) -> "Path | None":
    """Compile cpp_code, save .latest_binary, return binary Path or None on failure."""
    print("\n[compile] Compiling C++ (with SHA-256 caching)...")
    try:
        compiler = Compiler(cache_dir=_BUILD_DIR, cpp_dir=_CPP_DIR)
        binary = compiler.get_or_compile(cpp_code, "consensus")
        stats = compiler.get_cache_stats()
        print(f"    ✓ Binary: {binary}")
        print(f"    Cache: {stats['cached_binaries']} binaries, "
              f"{stats['cache_dir_size_bytes']} bytes")
        _BUILD_DIR.mkdir(parents=True, exist_ok=True)
        _BIN_LATEST.write_text(str(binary))
        print(f"    ✓ Path saved → {_BIN_LATEST}")
        return binary
    except Exception as exc:
        print(f"    ✗ {exc}")
        print("       (requires FCPP headers — see TUTORIAL_simple.md §Prerequisites)")
        return None


def step_run(binary_path: "Path | None", num_nodes: int, num_rounds: int) -> bool:
    """Pure-Python consensus simulation (binary_path shown for reference but not invoked)."""
    print(f"\n[run] Simulating swarm  ({num_nodes} nodes, {num_rounds} rounds)...")
    if binary_path is not None:
        print(f"    Binary available: {binary_path}")
        print("    (pure-Python simulation used here; wire SwarmProcess to invoke the binary)")

    try:
        import random
        random.seed(42)
        nodes = {i: random.uniform(0.0, 100.0) for i in range(num_nodes)}

        print(f"    Round 0: {[f'{v:.1f}' for v in list(nodes.values())[:5]]} ...")
        for rnd in range(1, num_rounds + 1):
            new = {}
            for nid in range(num_nodes):
                nbrs = [
                    nodes[n] for n in range(num_nodes)
                    if abs(n - nid) <= 2 and n != nid
                ]
                new[nid] = max(nodes[nid], max(nbrs)) if nbrs else nodes[nid]
            nodes = new

            vals = list(nodes.values())
            converged = len({round(v, 1) for v in vals}) == 1
            if rnd % max(1, num_rounds // 3) == 0 or converged:
                print(f"    Round {rnd:2d}: max={max(vals):.1f}  min={min(vals):.1f}  "
                      f"converged={converged}")
            if converged:
                print(f"    → Consensus reached at round {rnd}!")
                break

        print("    ✓ Simulation complete")
        final = sorted(nodes.values(), reverse=True)
        print(f"    Top-5 final values: {[f'{v:.2f}' for v in final[:5]]}")
        return True
    except Exception as exc:
        print(f"    ✗ {exc}")
        return False


# ── CLI helpers ───────────────────────────────────────────────────────────────

def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="end_to_end.py",
        description="FCPP Bridge end-to-end example with per-step execution control.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Step names:  validate  transpile  compile  run\n\n"
            "Examples:\n"
            "  python end_to_end.py                             # all steps\n"
            "  python end_to_end.py --from compile              # skip validate+transpile\n"
            "  python end_to_end.py --from run                  # skip compile too\n"
            "  python end_to_end.py --steps validate transpile  # only first two\n"
            "  python end_to_end.py --steps compile             # only compile\n"
            "\n"
            "Disk artifacts (so resuming a later step works):\n"
            f"  transpile writes: {_CPP_LATEST}\n"
            f"  compile   writes: {_BIN_LATEST}\n"
        ),
    )
    p.add_argument("--nodes",  type=int, default=10, metavar="N",
                   help="simulated node count (default: 10)")
    p.add_argument("--rounds", type=int, default=8,  metavar="N",
                   help="simulation rounds (default: 8)")

    group = p.add_mutually_exclusive_group()
    group.add_argument(
        "--steps", nargs="+", choices=STEPS, metavar="STEP",
        help="explicit list of steps to execute (any subset, in canonical order)",
    )
    group.add_argument(
        "--from", dest="from_step", choices=STEPS, metavar="STEP",
        help="run this step and every step that follows it",
    )
    return p.parse_args()


def _active_steps(args: argparse.Namespace) -> list:
    """Return the ordered subset of STEPS to run."""
    if args.steps:
        given = set(args.steps)
        return [s for s in STEPS if s in given]
    if args.from_step:
        return STEPS[STEPS.index(args.from_step):]
    return list(STEPS)


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    args = _parse_args()
    active = _active_steps(args)

    print("\n" + "=" * 70)
    print("FCPP Bridge — End-to-End Example")
    print(f"Steps to run:  {' → '.join(active)}")
    print("=" * 70)

    # ── Load artifacts whose generating step is being skipped ────────────────
    cpp_code:    "str | None"  = None
    binary_path: "Path | None" = None

    if "compile" in active and "transpile" not in active:
        if not _CPP_LATEST.exists():
            print(f"\n[error] 'compile' requires a prior transpile run.")
            print(f"        Expected artifact: {_CPP_LATEST}")
            print(f"        Run:  python end_to_end.py --steps transpile")
            sys.exit(1)
        cpp_code = _CPP_LATEST.read_text()
        print(f"\n[load] C++ source ← {_CPP_LATEST}  ({len(cpp_code)} bytes)")

    if "run" in active and "compile" not in active:
        if _BIN_LATEST.exists():
            binary_path = Path(_BIN_LATEST.read_text().strip())
            print(f"\n[load] Binary path ← {_BIN_LATEST}: {binary_path}")
        # binary_path may still be None if compile never ran; step_run handles that gracefully

    # ── Execute active steps ──────────────────────────────────────────────────
    if "validate" in active:
        if not step_validate():
            sys.exit(1)

    if "transpile" in active:
        cpp_code = step_transpile()
        if cpp_code is None:
            sys.exit(1)

    if "compile" in active:
        binary_path = step_compile(cpp_code)
        if binary_path is None:
            sys.exit(1)

    if "run" in active:
        if not step_run(binary_path, args.nodes, args.rounds):
            sys.exit(1)

    print("\n" + "=" * 70)
    print("Done.")
    print("=" * 70 + "\n")

    if active == ["validate", "transpile"] or active == ["transpile"]:
        print("Next step:  python end_to_end.py --from compile")
    elif active == ["compile"] or active == ["validate", "transpile", "compile"]:
        print("Next step:  python end_to_end.py --from run")


if __name__ == "__main__":
    main()
