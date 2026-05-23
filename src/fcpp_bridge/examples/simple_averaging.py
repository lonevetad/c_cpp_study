"""Example 1: Simple averaging aggregate function.

This shows the intended Python DSL usage after Phase 1-3 are complete.
Currently, this is pseudocode — the transpiler doesn't exist yet.

TODO: Implement phases 1-3, then this example will work.
"""

from fcpp_bridge.python_dsl import aggregate_function, Neighborhood


@aggregate_function
class AveragingAggregate:
    """
    Simple aggregate: each node computes weighted average of neighbors.

    Formula:
        state' = 0.7 * state + 0.3 * avg(neighbors)
    """

    def initial_state(self) -> float:
        """Start with zero state."""
        return 0.0

    def compute(self, self_state: float, neighbors: Neighborhood[float]) -> float:
        """Update state by averaging with neighbors."""
        if not neighbors.values:
            return self_state  # isolated node: no change

        neighbor_avg = sum(neighbors.values) / len(neighbors.values)
        return 0.7 * self_state + 0.3 * neighbor_avg


if __name__ == "__main__":
    # After Phase 3 is complete, this will work:
    # from fcpp_bridge.transpiler import Transpiler
    # from fcpp_bridge.compiler import Compiler
    # from fcpp_bridge.ipc import UnixSocketBackend, SwarmProcess
    #
    # # Transpile to C++
    # transpiler = Transpiler(AveragingAggregate)
    # cpp_code = transpiler.generate()
    # print(f"Generated {len(cpp_code)} bytes of C++ code")
    #
    # # Compile
    # compiler = Compiler()
    # binary_path = compiler.get_or_compile(cpp_code)
    # print(f"Compiled to: {binary_path}")
    #
    # # Run swarm
    # swarm = SwarmProcess(binary_path, num_nodes=100, ipc_backend="unix")
    # with swarm:
    #     for step in range(10):
    #         swarm.step()
    #         state = swarm.get_state()
    #         print(f"Step {step}: {len(state['nodes'])} nodes")

    print("Example 1: Averaging aggregate (pseudocode)")
    print("Phase 1-3 required before this runs.")
