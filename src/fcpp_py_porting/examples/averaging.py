"""
Example: Simple fcpp aggregate computing simulation with Python callbacks.

Demonstrates:
- Creating a simulation with Python callbacks
- Accessing device state and neighbor information
- Running the simulation to completion
"""

from fcpp_py import Simulation


def main():
    """Run example simulation with averaging aggregate function."""

    info = Simulation.compile_info()
    print(f"Simulation compile-time config:")
    print(f"  State size:  {info['state_size']} doubles/device")
    print(f"  Max devices: {info['max_devices']}")
    print(f"  Dimension:   {info['dimension']}D")
    print()

    with Simulation() as sim:
        print(f"Created simulation with {sim.device_count()} devices")

        # Define aggregate function: averaging
        def averaging_step(dev_id, time, self_state, neighbor_ids, neighbor_states):
            """
            Aggregate step: each device averages its state with neighbors.
            self_state: list of floats (previous exported state)
            neighbor_ids: list of neighbor device IDs
            neighbor_states: list of lists (each neighbor's previous state)
            returns: new state to export this round
            """
            if not neighbor_states:
                # No neighbors: keep current state (with small decay)
                return [x * 0.99 for x in self_state]

            # Average over neighbors
            averaged = [
                sum(nbr[i] for nbr in neighbor_states) / len(neighbor_states)
                for i in range(len(self_state))
            ]

            # Blend: 70% self, 30% neighbor average
            blended = [0.7 * s + 0.3 * a for s, a in zip(self_state, averaged)]
            return blended

        sim.set_callback(averaging_step)

        # Run for 2 time units, stepping one event at a time
        print("\nRunning simulation (manual stepping):")
        step_count = 0
        while sim.next_time() > -1 and step_count < 20:
            t = sim.next_time()
            sim.step()
            step_count += 1
            if step_count <= 5 or step_count % 5 == 0:
                ids, states = sim.get_all_states()
                avg_state = [
                    sum(s[i] for s in states) / len(states)
                    for i in range(len(states[0]))
                ] if states else []
                print(f"  Step {step_count}: time={t:.4f}, devices={len(ids)}, "
                      f"avg_state[0]={avg_state[0] if avg_state else 0:.6f}")

        print(f"\nCompleted {step_count} steps")

        # Sample final states
        ids, states = sim.get_all_states()
        print(f"\nFinal state summary ({len(ids)} devices):")
        for i, (dev_id, state) in enumerate(zip(ids[:3], states[:3])):
            print(f"  Device {dev_id}: {state}")
        if len(ids) > 3:
            print(f"  ... and {len(ids) - 3} more")


if __name__ == "__main__":
    main()
