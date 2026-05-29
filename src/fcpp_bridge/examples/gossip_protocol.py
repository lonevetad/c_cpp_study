"""Example 2: Gossip protocol aggregate function.

Demonstrates using the gossip mixin for distributed max aggregation.
"""

from fcpp_bridge.python_dsl import (
    aggregate_function,
    mixin_gossip,
    Neighborhood,
)


@aggregate_function
@mixin_gossip
class GossipMaxAggregate:
    """
    Gossip protocol: each node learns the maximum value from all nodes.

    Useful for:
    - Distributed consensus on maximum metric
    - Network-wide monitoring (e.g., max temperature, max resource usage)
    """

    def initial_state(self) -> float:
        """Start with random/small value."""
        import random
        return random.uniform(0.0, 100.0)

    def compute(self, self_state: float, neighbors: Neighborhood[float]) -> float:
        """Update to maximum seen so far."""
        if not neighbors.values:
            return self_state

        neighbor_max = max(neighbors.values)
        return max(self_state, neighbor_max)


if __name__ == "__main__":
    from fcpp_bridge.python_dsl.validators import AggregateValidator

    warnings = AggregateValidator.validate(GossipMaxAggregate)
    print(f"✓ GossipMaxAggregate is valid (warnings: {len(warnings)})")
    for w in warnings:
        print(f"  - {w}")
