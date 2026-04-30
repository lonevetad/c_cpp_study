"""Tests for fcpp_py Simulation bridge."""

import pytest
from fcpp_py import Simulation, Vec3


class TestSimulationBasics:
    """Basic simulation lifecycle tests."""

    def test_compile_info(self) -> None:
        """Check compile-time constants."""
        info = Simulation.compile_info()
        assert info["state_size"] == 8
        assert info["max_devices"] == 100
        assert info["dimension"] == 3

    def test_create_destroy(self) -> None:
        """Create and destroy simulation."""
        sim = Simulation()
        # Need to step at least once to spawn devices
        if sim.next_time() >= 0:
            sim.step()
        assert sim.device_count() > 0
        sim.destroy()

    def test_context_manager(self) -> None:
        """Test context manager protocol."""
        with Simulation() as sim:
            # Step at least once to spawn devices
            if sim.next_time() >= 0:
                sim.step()
            assert sim.device_count() > 0
        # should auto-destroy


class TestSimulationState:
    """Device state access tests."""

    def test_get_ids(self) -> None:
        """Get device IDs."""
        with Simulation() as sim:
            # Step to spawn devices
            if sim.next_time() >= 0:
                sim.step()
            ids = sim.get_ids()
            assert len(ids) > 0
            assert all(isinstance(i, int) for i in ids)

    def test_get_state(self) -> None:
        """Get single device state."""
        with Simulation() as sim:
            ids = sim.get_ids()
            if ids:
                state = sim.get_state(ids[0])
                assert state is not None
                assert len(state) == 8

    def test_get_all_states(self) -> None:
        """Get all device states."""
        with Simulation() as sim:
            ids_out, states_out = sim.get_all_states()
            assert len(ids_out) == len(states_out)
            for state in states_out:
                assert len(state) == 8


class TestSimulationCallback:
    """Python callback integration tests."""

    def test_set_callback(self) -> None:
        """Register and use callback."""
        with Simulation() as sim:
            call_count = [0]

            def callback(dev_id, t, self_prev, nbr_ids, nbr_states):
                call_count[0] += 1
                # Return new state: decay previous by half
                return [x * 0.99 for x in self_prev]

            sim.set_callback(callback)
            # Spawn devices and step
            if sim.next_time() >= 0:
                sim.step()
                sim.step()
            assert call_count[0] > 0

    def test_callback_with_neighbors(self) -> None:
        """Callback sees neighbor states."""
        with Simulation() as sim:
            neighbor_counts = []

            def callback(dev_id, t, self_prev, nbr_ids, nbr_states):
                neighbor_counts.append(len(nbr_ids))
                return self_prev

            sim.set_callback(callback)
            for _ in range(5):
                if sim.next_time() > -1:
                    sim.step()
            # Some devices should have neighbors
            assert any(n > 0 for n in neighbor_counts)

    def test_callback_state_passthrough(self) -> None:
        """Callback state changes propagate."""
        with Simulation() as sim:
            def callback(dev_id, t, self_prev, nbr_ids, nbr_states):
                # Echo neighbor count into first state element
                return [float(len(nbr_ids))] + self_prev[1:]

            sim.set_callback(callback)
            sim.run(1.0)  # run to time 1.0
            ids_out, states_out = sim.get_all_states()
            # Check that at least some devices have non-zero first state
            assert any(states[0] > 0 for states in states_out)


class TestSimulationTiming:
    """Simulation time and stepping tests."""

    def test_next_time(self) -> None:
        """Get next scheduled event time."""
        with Simulation() as sim:
            t = sim.next_time()
            assert t >= 0 or t == -1  # valid event time or -1 (done)

    def test_step(self) -> None:
        """Step through events."""
        with Simulation() as sim:
            t1 = sim.next_time()
            if t1 > -1:
                t2 = sim.step()
                assert t2 >= t1 or t2 == -1

    def test_run(self) -> None:
        """Run simulation to time."""
        with Simulation() as sim:
            initial_time = sim.next_time()
            sim.run(0.5)  # run to time 0.5
            final_time = sim.next_time()
            # time should have advanced
            assert final_time > initial_time or final_time == -1


class TestSimulationErrors:
    """Error handling tests."""

    def test_invalid_callback(self) -> None:
        """Non-callable callback rejected."""
        with Simulation() as sim:
            with pytest.raises(TypeError):
                sim.set_callback("not callable")

    def test_get_state_nonexistent(self) -> None:
        """Nonexistent device returns None."""
        with Simulation() as sim:
            state = sim.get_state(999999)
            assert state is None


class TestSimulationIntegration:
    """End-to-end integration tests."""

    def test_full_cycle(self) -> None:
        """Full simulation lifecycle."""
        with Simulation() as sim:
            info = Simulation.compile_info()

            def moving_average(dev_id, t, self_prev, nbr_ids, nbr_states):
                """Average with neighbors."""
                if not nbr_states:
                    return self_prev
                avg = [sum(nbr[i] for nbr in nbr_states) /
                       len(nbr_states) for i in range(8)]
                return [0.7 * s + 0.3 * a for s, a in zip(self_prev, avg)]

            sim.set_callback(moving_average)
            sim.run(2.0)  # 2 time units
            ids, states = sim.get_all_states()
            assert len(ids) > 0
            assert len(states) == len(ids)
            for state in states:
                assert len(state) == info["state_size"]

    def test_many_steps(self) -> None:
        """Run many steps without crash."""
        with Simulation() as sim:
            def noop(dev_id, t, self_prev, nbr_ids, nbr_states):
                return self_prev

            sim.set_callback(noop)
            for _ in range(100):
                if sim.next_time() > -1:
                    sim.step()
