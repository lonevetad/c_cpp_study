"""Example 3: Distance-based broadcast from source node.

Demonstrates using the broadcast mixin for disseminating values from a source.
"""

from dataclasses import dataclass
from fcpp_bridge.python_dsl import (
    aggregate_function,
    mixin_broadcast,
    Neighborhood,
)


@dataclass
class BroadcastState:
    """State: value received from broadcast + distance."""
    value: float
    distance: int


@aggregate_function
@mixin_broadcast
class DistanceBroadcastAggregate:
    """
    Distance-based broadcast: propagate a value from source through the network.

    The source node (ID 0) broadcasts a value. Other nodes receive it,
    incrementing distance each hop.

    Useful for:
    - Flooding with distance tracking
    - Leader election with distance metric
    - Wave propagation from a source
    """

    def initial_state(self) -> BroadcastState:
        """Start with large distance, no value."""
        return BroadcastState(value=0.0, distance=999)

    def compute(
        self, self_state: BroadcastState, neighbors: Neighborhood[BroadcastState]
    ) -> BroadcastState:
        """
        Update to minimum distance from source.

        If neighbors have closer source, adopt their value and increment distance.
        """
        if not neighbors.values:
            return self_state

        # Find neighbor with minimum distance
        closest = min(neighbors.values, key=lambda n: n.distance)

        # If neighbor is closer, adopt their value and add 1 to distance
        if closest.distance + 1 < self_state.distance:
            return BroadcastState(
                value=closest.value,
                distance=closest.distance + 1
            )

        return self_state


if __name__ == "__main__":
    from fcpp_bridge.python_dsl.validators import AggregateValidator

    warnings = AggregateValidator.validate(DistanceBroadcastAggregate)
    print(f"✓ DistanceBroadcastAggregate is valid (warnings: {len(warnings)})")
    for w in warnings:
        print(f"  - {w}")
