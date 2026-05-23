"""Pre-transpilation validation for aggregate functions."""

import inspect
from typing import Any, Type, List, get_type_hints, get_origin, get_args
from .primitives import Field, Neighborhood, OldValue


class ValidationError(Exception):
    """Raised when DSL validation fails."""

    pass


class AggregateValidator:
    """Validates aggregate function classes before transpilation."""

    REQUIRED_METHODS = ["initial_state", "compute"]
    OPTIONAL_METHODS = ["when_source", "when_merge"]  # event handlers

    @staticmethod
    def validate(cls: Type) -> List[str]:
        """
        Validate aggregate function class.

        Returns list of warnings (empty list = valid).
        Raises ValidationError on critical failures.
        """
        warnings = []

        # Check marker
        if not getattr(cls, "_is_aggregate_function", False):
            raise ValidationError(f"{cls.__name__} is not decorated with @aggregate_function")

        # Check required methods
        for method_name in AggregateValidator.REQUIRED_METHODS:
            method = getattr(cls, method_name, None)
            if not callable(method):
                raise ValidationError(f"{cls.__name__}.{method_name}() is required and must be callable")

        # Validate method signatures
        AggregateValidator._validate_initial_state(cls)
        AggregateValidator._validate_compute(cls)

        # Check for common mistakes
        if hasattr(cls, "step"):
            warnings.append(f"{cls.__name__} defines step() but should use compute()")

        if hasattr(cls, "update"):
            warnings.append(f"{cls.__name__} defines update() but should use compute()")

        return warnings

    @staticmethod
    def _validate_initial_state(cls: Type) -> None:
        """Validate initial_state method signature and return type."""
        method = getattr(cls, "initial_state")
        sig = inspect.signature(method)

        # Should only have 'self' parameter
        params = list(sig.parameters.keys())
        if params and params[0] == "self":
            params = params[1:]

        if params:
            raise ValidationError(
                f"{cls.__name__}.initial_state() takes no parameters (got {len(params)})"
            )

        # Must have return type annotation
        if sig.return_annotation == inspect.Signature.empty:
            raise ValidationError(
                f"{cls.__name__}.initial_state() must have return type annotation "
                "(e.g., '-> float' or '-> MyState')"
            )

    @staticmethod
    def _validate_compute(cls: Type) -> None:
        """Validate compute method signature and parameter types."""
        method = getattr(cls, "compute")
        sig = inspect.signature(method)

        params = list(sig.parameters.keys())
        if params and params[0] == "self":
            params = params[1:]

        # Should have exactly 2 parameters: self_state and neighbors
        if len(params) != 2:
            raise ValidationError(
                f"{cls.__name__}.compute() must have exactly 2 parameters "
                f"(self_state, neighbors), got {len(params)}"
            )

        if params[0] not in ("self_state", "state", "s"):
            raise ValidationError(
                f"{cls.__name__}.compute() first parameter should be 'self_state' "
                f"(got '{params[0]}')"
            )

        if params[1] not in ("neighbors", "nbrs", "neighborhood"):
            raise ValidationError(
                f"{cls.__name__}.compute() second parameter should be 'neighbors' "
                f"(got '{params[1]}')"
            )

        # Must have return type annotation
        if sig.return_annotation == inspect.Signature.empty:
            raise ValidationError(
                f"{cls.__name__}.compute() must have return type annotation"
            )

    @staticmethod
    def get_state_type(cls: Type) -> Type:
        """Extract state type from initial_state() return annotation."""
        method = getattr(cls, "initial_state")
        sig = inspect.signature(method)

        if sig.return_annotation == inspect.Signature.empty:
            raise ValidationError(f"{cls.__name__}.initial_state() must have return type annotation")

        return sig.return_annotation

    @staticmethod
    def is_supported_type(py_type: Type) -> bool:
        """Check if type is supported for code generation."""
        from .types import AggregateType

        try:
            AggregateType.infer(py_type)
            return True
        except ValueError:
            return False

    @staticmethod
    def check_method_signature(method: Any, expected_params: List[str]) -> bool:
        """Verify method has expected parameters."""
        sig = inspect.signature(method)
        actual_params = list(sig.parameters.keys())

        # Remove 'self' if present
        if actual_params and actual_params[0] == "self":
            actual_params = actual_params[1:]

        return actual_params == expected_params
