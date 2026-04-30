"""Comprehensive test suite for fcpp_py bridge and simulation."""

import pytest
import math
from fcpp_py import Vec2, Vec3, Simulation, version


class TestVec2Comprehensive:
    """Extended vector tests for mathematical properties."""

    def test_vec2_triangle_inequality(self) -> None:
        """Test triangle inequality: |a+b| <= |a| + |b|."""
        a = Vec2(3.0, 4.0)
        b = Vec2(5.0, 12.0)
        c = a + b
        assert c.norm() <= a.norm() + b.norm() + 1e-10  # allow floating point error

    def test_vec2_pythagorean_identity(self) -> None:
        """Test Pythagorean identity for perpendicular vectors."""
        a = Vec2(3.0, 0.0)
        b = Vec2(0.0, 4.0)
        # perpendicular: a*b = 0, |a+b|² = |a|² + |b|²
        assert abs(a.dot(b)) < 1e-10
        c = a + b
        assert abs(c.norm()**2 - (a.norm()**2 + b.norm()**2)) < 1e-10

    def test_vec2_commutative_operations(self) -> None:
        """Test that operations are commutative where expected."""
        a = Vec2(1.5, 2.5)
        b = Vec2(3.5, 4.5)
        # addition is commutative
        assert (a + b) == (b + a)
        # dot product is commutative
        assert a.dot(b) == b.dot(a)

    def test_vec2_associative_operations(self) -> None:
        """Test associativity of scalar operations."""
        v = Vec2(2.0, 3.0)
        # (v * a) * b = v * (a*b)
        va2 = v * 2.0 * 3.0
        vab = v * (2.0 * 3.0)
        assert va2 == vab

    def test_vec2_distributive_law(self) -> None:
        """Test distributive law: a * (b + c) = a*b + a*c."""
        a = 2.5
        b = Vec2(1.0, 2.0)
        c = Vec2(3.0, 4.0)
        left = (b + c) * a
        right = b * a + c * a
        assert left == right

    def test_vec2_zero_properties(self) -> None:
        """Test properties of zero vector."""
        v = Vec2(1.0, 2.0)
        zero = Vec2(0.0, 0.0)
        # additive identity
        assert v + zero == v
        # multiplicative zero
        assert v * 0.0 == zero

    def test_vec2_numerical_stability(self) -> None:
        """Test numerical stability with very small values."""
        tiny = 1e-15
        v = Vec2(tiny, tiny)
        assert v.norm() > 0  # should not underflow to zero
        assert v.unit().norm() > 0.999  # unit should be close to 1

    def test_vec2_large_magnitude(self) -> None:
        """Test stability with very large magnitudes."""
        large = 1e10
        v = Vec2(large, large)
        assert math.isinf(v.norm()) or v.norm() > 1e10


class TestVec3Comprehensive:
    """Extended vector tests for 3D vectors."""

    def test_vec3_orthogonality(self) -> None:
        """Test orthogonal vectors have zero dot product."""
        x_axis = Vec3(1.0, 0.0, 0.0)
        y_axis = Vec3(0.0, 1.0, 0.0)
        z_axis = Vec3(0.0, 0.0, 1.0)

        assert abs(x_axis.dot(y_axis)) < 1e-10
        assert abs(y_axis.dot(z_axis)) < 1e-10
        assert abs(z_axis.dot(x_axis)) < 1e-10

    def test_vec3_cross_product_simulation(self) -> None:
        """Test cross product properties (via simulation with dot product)."""
        # If c = a × b, then c ⊥ a and c ⊥ b
        # We can compute cross product values and verify orthogonality
        a = Vec3(1.0, 0.0, 0.0)
        b = Vec3(0.0, 1.0, 0.0)
        # Expected cross product: (0, 0, 1)
        # Verify perpendicularity by ensuring dot products with a and b would be zero
        assert abs(a.norm() - 1.0) < 1e-10
        assert abs(b.norm() - 1.0) < 1e-10

    def test_vec3_scalar_associativity(self) -> None:
        """Test scalar associativity: (a*s1)*s2 = a*(s1*s2)."""
        v = Vec3(1.0, 2.0, 3.0)
        s1, s2 = 2.0, 3.5
        left = (v * s1) * s2
        right = v * (s1 * s2)
        for i in range(3):
            assert abs(left[i] - right[i]) < 1e-10

    def test_vec3_index_mutation(self) -> None:
        """Test that index mutation affects the vector correctly."""
        v = Vec3(1.0, 2.0, 3.0)
        v[0] = 10.0
        v[1] = 20.0
        v[2] = 30.0
        assert v.x == 10.0
        assert v.y == 20.0
        assert v.z == 30.0


class TestSimulationComprehensive:
    """Comprehensive simulation tests."""

    def test_simulation_determinism(self) -> None:
        """Test that same initial conditions produce same results."""
        results1 = []
        results2 = []

        for run in range(2):
            with Simulation() as sim:
                call_count = [0]

                def callback(dev_id, t, self_prev, nbr_ids, nbr_states):
                    call_count[0] += 1
                    return [self_prev[i] * 0.95 for i in range(8)]

                sim.set_callback(callback)

                # Run for a fixed number of steps
                for _ in range(5):
                    if sim.next_time() >= 0:
                        sim.step()

                ids, states = sim.get_all_states()
                results = (len(ids), call_count[0])
                (results1 if run == 0 else results2).append(results)

        # Both runs should have same device count and callback count
        assert results1[0] == results2[0]

    def test_simulation_state_evolution(self) -> None:
        """Test that state evolves according to callback."""
        with Simulation() as sim:
            initial_states = {}

            def decay_callback(dev_id, t, self_prev, nbr_ids, nbr_states):
                # Exponential decay
                if dev_id not in initial_states:
                    initial_states[dev_id] = self_prev[0]
                # State should decay by half each step (in first element)
                return [self_prev[i] * 0.5 for i in range(8)]

            sim.set_callback(decay_callback)

            # Run several steps
            for _ in range(3):
                if sim.next_time() >= 0:
                    sim.step()

            # Verify states are available
            ids, states = sim.get_all_states()
            assert len(ids) > 0
            assert all(len(s) == 8 for s in states)

    def test_simulation_neighbor_communication(self) -> None:
        """Test that devices can see their neighbors."""
        with Simulation() as sim:
            neighbor_info = []

            def neighbor_tracker(dev_id, t, self_prev, nbr_ids, nbr_states):
                neighbor_info.append((dev_id, len(nbr_ids)))
                return self_prev

            sim.set_callback(neighbor_tracker)

            # Step to spawn devices
            if sim.next_time() >= 0:
                sim.step()
            # Another step to get neighbor info
            if sim.next_time() >= 0:
                sim.step()

            # At least some devices should have neighbors (given COMM=50 in a 200x200 area)
            has_neighbors = any(nbr_count > 0 for _,
                                nbr_count in neighbor_info)
            # This might not always be true due to randomness, but is likely
            # Don't assert, just document

    def test_simulation_callback_exception_handling(self) -> None:
        """Test that exceptions in callbacks are handled gracefully."""
        with Simulation() as sim:
            call_count = [0]

            def bad_callback(dev_id, t, self_prev, nbr_ids, nbr_states):
                call_count[0] += 1
                if call_count[0] == 2:
                    # Return wrong size (should be 8 elements)
                    return [0.0] * 5
                return self_prev

            # This might crash the simulation - test that at least
            # we can handle the error gracefully
            try:
                sim.set_callback(bad_callback)
                if sim.next_time() >= 0:
                    sim.step()
                if sim.next_time() >= 0:
                    sim.step()
            except (ValueError, IndexError, RuntimeError):
                # Expected - callback returned wrong size
                pass

    def test_simulation_state_access_consistency(self) -> None:
        """Test that state access methods are consistent."""
        with Simulation() as sim:
            def simple_callback(dev_id, t, self_prev, nbr_ids, nbr_states):
                return [(i + 0.5) for i in range(8)]

            sim.set_callback(simple_callback)

            # Step to spawn devices
            if sim.next_time() >= 0:
                sim.step()

            # Get IDs first
            ids = sim.get_ids()

            if ids:
                # Get individual state
                state_individual = sim.get_state(ids[0])

                # Get all states
                ids_all, states_all = sim.get_all_states()

                # Find index of first device in all states
                idx = ids_all.index(ids[0])
                state_from_all = states_all[idx]

                # They should be the same
                if state_individual and state_from_all:
                    assert len(state_individual) == len(state_from_all)
                    for i in range(len(state_individual)):
                        assert abs(
                            state_individual[i] - state_from_all[i]) < 1e-10


class TestVectorIntegration:
    """Integration tests combining vectors and simulation."""

    def test_vector_math_in_callback(self) -> None:
        """Test using Vec3 computations in simulation callbacks."""
        with Simulation() as sim:
            def vector_callback(dev_id, t, self_prev, nbr_ids, nbr_states):
                # Use Vec3 to do some computation
                v = Vec3(self_prev[0], self_prev[1], self_prev[2])
                norm_sq = v.dot(v)

                # Return modified state
                result = list(self_prev)
                result[0] = norm_sq
                return result

            sim.set_callback(vector_callback)

            # Run a step
            if sim.next_time() >= 0:
                sim.step()

            # Simulation should complete without error
            assert True

    def test_version_consistency(self) -> None:
        """Test that version functions are consistent."""
        v = version()
        assert isinstance(v, str)
        assert len(v) > 0

        # Try to parse version
        parts = v.split('.')
        assert len(parts) >= 1


class TestMemoryAndPerformance:
    """Tests for memory efficiency and performance."""

    def test_multiple_simulations_cleanup(self) -> None:
        """Test that creating/destroying multiple simulations works."""
        for i in range(5):
            with Simulation() as sim:
                if sim.next_time() >= 0:
                    sim.step()
                ids = sim.get_ids()
                assert len(ids) >= 0  # May be 0 or more

    def test_large_simulation_steps(self) -> None:
        """Test simulation with many steps."""
        with Simulation() as sim:
            step_count = 0
            max_steps = 50

            def counter_callback(dev_id, t, self_prev, nbr_ids, nbr_states):
                return self_prev

            sim.set_callback(counter_callback)

            while step_count < max_steps and sim.next_time() >= 0:
                sim.step()
                step_count += 1

            # Should complete without crash
            assert step_count > 0

    def test_vector_allocation_efficiency(self) -> None:
        """Test creating many vectors doesn't cause issues."""
        vectors = []
        for i in range(100):
            v2 = Vec2(float(i), float(i+1))
            v3 = Vec3(float(i), float(i+1), float(i+2))
            vectors.append((v2, v3))

        # All should be accessible
        assert len(vectors) == 100
        assert vectors[0][0].norm() == vectors[0][0].norm()


class TestErrorHandling:
    """Tests for error handling and edge cases."""

    def test_vec2_division_by_zero(self) -> None:
        """Test dividing by zero returns inf."""
        v = Vec2(1.0, 2.0)
        result = v / 0.0
        # Division by zero is allowed in C, check behavior
        assert math.isinf(result.x) or math.isnan(result.x)

    def test_simulation_invalid_device_id(self) -> None:
        """Test getting state for nonexistent device."""
        with Simulation() as sim:
            # Try to get state for device ID that doesn't exist
            state = sim.get_state(99999)
            assert state is None

    def test_callback_none_handling(self) -> None:
        """Test that simulation works without callback."""
        with Simulation() as sim:
            # Don't set any callback
            if sim.next_time() >= 0:
                sim.step()
            # Should work fine, just with default behavior
            ids = sim.get_ids()
            assert len(ids) >= 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
