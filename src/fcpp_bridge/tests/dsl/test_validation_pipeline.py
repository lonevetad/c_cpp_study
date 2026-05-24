"""Tests for ValidationRule ABC and ValidationPipeline (v0.9)."""

import pytest
from fcpp_bridge.python_dsl import aggregate_function, Neighborhood
from fcpp_bridge.python_dsl.validators import (
    AggregateValidator,
    ValidationError,
    ValidationRule,
    ValidationPipeline,
    MarkerRule,
    RequiredMethodsRule,
    InitialStateRule,
    ComputeSignatureRule,
    DeprecatedMethodRule,
)


def test_validation_rule_is_abstract():
    with pytest.raises(TypeError):
        ValidationRule()  # type: ignore


def test_validation_pipeline_empty_passes():
    pipeline = ValidationPipeline()

    @aggregate_function
    class Dummy:
        def initial_state(self) -> float:
            return 0.0
        def compute(self, self_state: float, neighbors) -> float:
            return self_state

    assert pipeline.run(Dummy) == []


def test_validation_pipeline_custom_rule():
    class RequireDocstringRule(ValidationRule):
        def check(self, cls):
            if not cls.__doc__:
                return [f"{cls.__name__} is missing a class docstring"]
            return []

    pipeline = ValidationPipeline([RequireDocstringRule()])

    @aggregate_function
    class WithDoc:
        """Has a docstring."""
        def initial_state(self) -> float:
            return 0.0
        def compute(self, self_state: float, neighbors) -> float:
            return self_state

    @aggregate_function
    class NoDoc:
        def initial_state(self) -> float:
            return 0.0
        def compute(self, self_state: float, neighbors) -> float:
            return self_state

    assert pipeline.run(WithDoc) == []
    warnings = pipeline.run(NoDoc)
    assert any("docstring" in w for w in warnings)


def test_validation_pipeline_raises_on_bad_class():
    pipeline = ValidationPipeline([MarkerRule()])

    class NotDecorated:
        def initial_state(self) -> float:
            return 0.0
        def compute(self, self_state: float, neighbors) -> float:
            return self_state

    with pytest.raises(ValidationError):
        pipeline.run(NotDecorated)


def test_aggregate_validator_uses_pipeline():
    @aggregate_function
    class ValidClass:
        def initial_state(self) -> int:
            return 0
        def compute(self, self_state: int, neighbors) -> int:
            return self_state + 1

    warnings = AggregateValidator.validate(ValidClass)
    assert isinstance(warnings, list)


def test_aggregate_validator_custom_pipeline():
    class AlwaysWarnRule(ValidationRule):
        def check(self, cls):
            return ["always warn"]

    original = AggregateValidator._pipeline
    AggregateValidator.set_pipeline(ValidationPipeline([AlwaysWarnRule()]))
    try:
        @aggregate_function
        class A:
            def initial_state(self) -> float:
                return 0.0
            def compute(self, self_state: float, neighbors) -> float:
                return self_state

        warnings = AggregateValidator.validate(A)
        assert "always warn" in warnings
    finally:
        AggregateValidator.set_pipeline(original)
