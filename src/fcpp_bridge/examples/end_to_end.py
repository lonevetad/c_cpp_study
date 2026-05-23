"""Example: End-to-end workflow from Python DSL to running swarm.

Demonstrates the complete pipeline:
1. Define aggregate in Python
2. Transpile to C++
3. Compile with caching
4. Run swarm via IPC
5. Collect & analyze results
"""

from fcpp_bridge.python_dsl import aggregate_function, Neighborhood, AggregateValidator
from fcpp_bridge.transpiler import Transpiler
from fcpp_bridge.compiler import Compiler
from pathlib import Path


@aggregate_function
class ConsensusAggregate:
    """
    Byzantine Consensus: Nodes agree on maximum value seen.

    Theory: A simple form of Byzantine-resilient consensus where
    nodes propagate the maximum observed value, reaching consensus
    over multiple rounds.

    Usage:
        swarm = EndToEndExample.run(num_rounds=10)
    """

    def initial_state(self) -> float:
        """Each node starts with a random value [0, 100]."""
        import random
        return random.uniform(0.0, 100.0)

    def compute(self, self_state: float, neighbors: Neighborhood[float]) -> float:
        """
        Update rule: take maximum of self and all neighbors.

        This guarantees convergence to the global maximum in O(diameter) rounds.
        """
        if not neighbors.values:
            return self_state

        max_neighbor = max(neighbors.values)
        return max(self_state, max_neighbor)


class EndToEndExample:
    """Complete pipeline: definition → transpilation → compilation → execution."""

    @staticmethod
    def run(num_nodes: int = 10, num_rounds: int = 5) -> None:
        """
        Run complete pipeline.

        Args:
            num_nodes: Number of nodes in swarm
            num_rounds: Simulation rounds
        """
        print("\n" + "="*70)
        print("FCPP Bridge - End-to-End Example")
        print("="*70 + "\n")

        # ====================================================================
        # Phase 1: Validate Python DSL
        # ====================================================================
        print("[1/4] Validating Python DSL...")
        try:
            warnings = AggregateValidator.validate(ConsensusAggregate)
            print(f"    ✓ DSL is valid ({len(warnings)} warnings)")
            for w in warnings:
                print(f"      - {w}")
        except Exception as e:
            print(f"    ✗ DSL validation failed: {e}")
            return

        # ====================================================================
        # Phase 2: Transpile to C++
        # ====================================================================
        print("\n[2/4] Transpiling to C++...")
        try:
            transpiler = Transpiler(ConsensusAggregate)
            cpp_code = transpiler.generate()
            print(f"    ✓ Generated {len(cpp_code)} bytes of C++ code")
            print(f"    State type: {transpiler.get_state_type_cpp().name}")
        except Exception as e:
            print(f"    ✗ Transpilation failed: {e}")
            return

        # ====================================================================
        # Phase 3: Compile with Caching
        # ====================================================================
        print("\n[3/4] Compiling C++ (with caching)...")
        try:
            compiler = Compiler(
                cache_dir=Path(".fcpp_bridge_build"),
                cpp_dir=Path(".fcpp_bridge_cpp"),
            )

            binary_path = compiler.get_or_compile(cpp_code, "consensus")
            stats = compiler.get_cache_stats()
            print(f"    ✓ Compiled to: {binary_path}")
            print(f"    Cache: {stats['cached_binaries']} binaries, "
                  f"{stats['cache_dir_size_bytes']} bytes")
        except Exception as e:
            print(f"    ✗ Compilation failed: {e}")
            print(f"       (Note: C++ compiler may not be available in test env)")
            return

        # ====================================================================
        # Phase 4: Execute Swarm (Simulated)
        # ====================================================================
        print("\n[4/4] Executing swarm simulation (simulated)...")
        print(f"    Nodes: {num_nodes}")
        print(f"    Rounds: {num_rounds}")

        try:
            # Note: Actual swarm execution requires the compiled binary to
            # be runnable. In a test environment, we demonstrate the flow.

            from fcpp_bridge.ipc import SwarmSnapshot, NodeState

            # Simulate swarm state evolution
            import random
            random.seed(42)

            # Initial state: random values
            nodes_state = {
                i: random.uniform(0.0, 100.0) for i in range(num_nodes)
            }

            print("\n    --- Simulation Progress ---")
            print(f"    Round 0: {[f'{v:.1f}' for v in list(nodes_state.values())[:5]]}...")

            # Simulate consensus rounds
            for round_num in range(1, num_rounds + 1):
                # Each node takes max of its value and neighbors
                new_state = {}
                for node_id in range(num_nodes):
                    # Find neighbors (simple: nodes within distance 2)
                    neighbor_ids = [
                        n for n in range(num_nodes)
                        if abs(n - node_id) <= 2 and n != node_id
                    ]
                    neighbor_values = [nodes_state[n] for n in neighbor_ids]

                    if neighbor_values:
                        new_state[node_id] = max(nodes_state[node_id], max(neighbor_values))
                    else:
                        new_state[node_id] = nodes_state[node_id]

                nodes_state = new_state

                # Check convergence
                values = list(nodes_state.values())
                converged = len(set(round(v, 1) for v in values)) == 1

                if round_num % max(1, num_rounds // 3) == 0 or converged:
                    print(f"    Round {round_num}: "
                          f"max={max(values):.1f}, min={min(values):.1f}, "
                          f"converged={converged}")

                if converged:
                    print(f"    -> Consensus reached in round {round_num}!")
                    break

            print("\n    ✓ Simulation complete")

            # Display final state
            final_values = sorted(nodes_state.values(), reverse=True)
            print(f"\n    Final state (top 5):")
            for i, val in enumerate(final_values[:5]):
                print(f"      {i+1}. {val:.2f}")

        except Exception as e:
            print(f"    ✗ Execution failed: {e}")
            return

        # ====================================================================
        # Summary
        # ====================================================================
        print("\n" + "="*70)
        print("✓ End-to-end pipeline completed successfully!")
        print("="*70 + "\n")

        print("Next steps:")
        print("  1. Modify ConsensusAggregate to test different algorithms")
        print("  2. Increase num_nodes for larger swarms")
        print("  3. Use parser: grammar.AggregateLanguageParser for DSL from strings")
        print("  4. Deploy to actual cluster with HTTP/gRPC backends")
        print()


if __name__ == "__main__":
    EndToEndExample.run(num_nodes=20, num_rounds=8)
