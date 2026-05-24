"""Tests for @aggregate_function decorator — validation, signatures, state types."""

import pytest
from dataclasses import dataclass
from fcpp_bridge.python_dsl import aggregate_function, Neighborhood, AggregateType
from fcpp_bridge.python_dsl.validators import AggregateValidator, ValidationError


# ============================================================================
# Test 1: Basic DSL decorator and validation
# ============================================================================


def test_dsl_basic_aggregate():
    @aggregate_function
    class SimpleAverage:
        def initial_state(self) -> float:
            return 0.0

        def compute(self, self_state: float, neighbors: Neighborhood[float]) -> float:
            if not neighbors.values:
                return self_state
            avg = sum(neighbors.values) / len(neighbors.values)
            return 0.7 * self_state + 0.3 * avg

    assert hasattr(SimpleAverage, "_is_aggregate_function")
    assert SimpleAverage._is_aggregate_function is True


def test_dsl_missing_decorator():
    class NotDecorated:
        def initial_state(self) -> float:
            return 0.0

        def compute(self, self_state: float, neighbors: Neighborhood[float]) -> float:
            return self_state

    with pytest.raises(ValidationError):
        AggregateValidator.validate(NotDecorated)


def test_dsl_missing_initial_state():
    with pytest.raises(ValueError, match="initial_state"):

        @aggregate_function
        class BadAggregate1:
            def compute(self, self_state, neighbors):
                return self_state


def test_dsl_missing_compute():
    with pytest.raises(ValueError, match="compute"):

        @aggregate_function
        class BadAggregate2:
            def initial_state(self) -> float:
                return 0.0


# ============================================================================
# Test 2: Type annotations validation
# ============================================================================


def test_dsl_missing_initial_state_return_type():
    with pytest.raises(ValidationError, match="return type annotation"):

        @aggregate_function
        class BadType1:
            def initial_state(self):  # missing return type
                return 0.0

            def compute(self, self_state: float, neighbors: Neighborhood[float]) -> float:
                return self_state


def test_dsl_missing_compute_return_type():
    with pytest.raises(ValidationError, match="return type annotation"):

        @aggregate_function
        class BadType2:
            def initial_state(self) -> float:
                return 0.0

            def compute(self, self_state: float, neighbors: Neighborhood[float]):  # missing return
                return self_state


# ============================================================================
# Test 3: Method signature validation
# ============================================================================


def test_dsl_compute_signature_wrong_param_count():
    with pytest.raises(ValidationError, match="exactly 2 parameters"):

        @aggregate_function
        class BadSig1:
            def initial_state(self) -> float:
                return 0.0

            def compute(self, self_state: float, neighbors: Neighborhood[float], extra) -> float:
                return self_state


def test_dsl_compute_signature_too_few_params():
    with pytest.raises(ValidationError, match="exactly 2 parameters"):

        @aggregate_function
        class BadSig2:
            def initial_state(self) -> float:
                return 0.0

            def compute(self, self_state: float) -> float:
                return self_state


def test_dsl_initial_state_with_params():
    with pytest.raises(ValidationError, match="takes no parameters"):

        @aggregate_function
        class BadSig3:
            def initial_state(self, x: float) -> float:
                return x

            def compute(self, self_state: float, neighbors: Neighborhood[float]) -> float:
                return self_state


# ============================================================================
# Test 4: Custom state types
# ============================================================================


def test_dsl_custom_struct_state():
    @dataclass
    class NodeState:
        value: float
        counter: int

    @aggregate_function
    class StructAggregate:
        def initial_state(self) -> NodeState:
            return NodeState(value=0.0, counter=0)

        def compute(
            self, self_state: NodeState, neighbors: Neighborhood[NodeState]
        ) -> NodeState:
            new_value = self_state.value + 1.0
            return NodeState(value=new_value, counter=self_state.counter + 1)

    validator = AggregateValidator()
    warnings = validator.validate(StructAggregate)
    assert len(warnings) == 0
    state_type = AggregateValidator.get_state_type(StructAggregate)
    assert state_type is NodeState


def test_dsl_tuple_state():
    @aggregate_function
    class TupleAggregate:
        def initial_state(self) -> tuple[float, int]:
            return (0.0, 0)

        def compute(
            self, self_state: tuple[float, int], neighbors: Neighborhood[tuple[float, int]]
        ) -> tuple[float, int]:
            value, count = self_state
            return (value + 1.0, count + 1)

    warnings = AggregateValidator.validate(TupleAggregate)
    assert len(warnings) == 0


def test_dsl_list_state():
    @aggregate_function
    class ListAggregate:
        def initial_state(self) -> list[float]:
            return [0.0, 0.0, 0.0]

        def compute(
            self, self_state: list[float], neighbors: Neighborhood[list[float]]
        ) -> list[float]:
            return [x + 1.0 for x in self_state]

    warnings = AggregateValidator.validate(ListAggregate)
    assert len(warnings) == 0


# ============================================================================
# Test 5: State type extraction
# ============================================================================


def test_dsl_extract_state_type_float():
    @aggregate_function
    class FloatAggregate:
        def initial_state(self) -> float:
            return 0.0

        def compute(self, self_state: float, neighbors: Neighborhood[float]) -> float:
            return self_state

    state_type = AggregateValidator.get_state_type(FloatAggregate)
    assert state_type is float


def test_dsl_extract_state_type_int():
    @aggregate_function
    class IntAggregate:
        def initial_state(self) -> int:
            return 0

        def compute(self, self_state: int, neighbors: Neighborhood[int]) -> int:
            return self_state

    state_type = AggregateValidator.get_state_type(IntAggregate)
    assert state_type is int


def test_dsl_extract_state_type_custom():
    @dataclass
    class CustomState:
        x: float
        y: int

    @aggregate_function
    class CustomAggregate:
        def initial_state(self) -> CustomState:
            return CustomState(0.0, 0)

        def compute(
            self, self_state: CustomState, neighbors: Neighborhood[CustomState]
        ) -> CustomState:
            return self_state

    state_type = AggregateValidator.get_state_type(CustomAggregate)
    assert state_type is CustomState


# ============================================================================
# Test 6: Common mistakes detection
# ============================================================================


def test_dsl_warning_step_method():
    @aggregate_function
    class HasStepMethod:
        def initial_state(self) -> float:
            return 0.0

        def compute(self, self_state: float, neighbors: Neighborhood[float]) -> float:
            return self_state

        def step(self):  # Common mistake
            pass

    warnings = AggregateValidator.validate(HasStepMethod)
    assert any("step" in w for w in warnings)


def test_dsl_warning_update_method():
    @aggregate_function
    class HasUpdateMethod:
        def initial_state(self) -> float:
            return 0.0

        def compute(self, self_state: float, neighbors: Neighborhood[float]) -> float:
            return self_state

        def update(self):  # Common mistake
            pass

    warnings = AggregateValidator.validate(HasUpdateMethod)
    assert any("update" in w for w in warnings)
