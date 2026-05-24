"""Pre-transpilation validation for aggregate functions."""

import inspect
from abc import ABC, abstractmethod
from typing import Any, Type, List

from fcpp_bridge.log import get_logger

_log = get_logger(__name__)


class ValidationError(Exception):
    """Raised when DSL validation fails."""
    pass


# ---------------------------------------------------------------------------
# ValidationRule ABC — single responsibility per check
# ---------------------------------------------------------------------------

class ValidationRule(ABC):
    """Abstract base for a single validation rule.

    ``check()`` returns a list of warning strings (empty = passed).
    Implementations raise :class:`ValidationError` for critical failures.
    """

    @abstractmethod
    def check(self, cls: Type) -> List[str]:
        """Validate *cls* and return warnings.  Raise ValidationError on failure."""
        ...


class MarkerRule(ValidationRule):
    """Require the ``_is_aggregate_function`` marker set by the decorator."""

    def check(self, cls: Type) -> List[str]:
        if not getattr(cls, "_is_aggregate_function", False):
            raise ValidationError(
                f"{cls.__name__} is not decorated with @aggregate_function"
            )
        return []


class RequiredMethodsRule(ValidationRule):
    """Require ``initial_state`` and ``compute`` to be callable."""

    _REQUIRED = ("initial_state", "compute")

    def check(self, cls: Type) -> List[str]:
        for name in self._REQUIRED:
            method = getattr(cls, name, None)
            if not callable(method):
                raise ValidationError(
                    f"{cls.__name__}.{name}() is required and must be callable"
                )
        return []


class InitialStateRule(ValidationRule):
    """Validate ``initial_state()`` takes no params and has a return annotation."""

    def check(self, cls: Type) -> List[str]:
        method = getattr(cls, "initial_state")
        sig = inspect.signature(method)

        params = [p for p in sig.parameters if p != "self"]
        if params:
            raise ValidationError(
                f"{cls.__name__}.initial_state() takes no parameters "
                f"(got {len(params)})"
            )

        if sig.return_annotation is inspect.Parameter.empty:
            raise ValidationError(
                f"{cls.__name__}.initial_state() must have return type annotation "
                "(e.g., '-> float' or '-> MyState')"
            )
        return []


class ComputeSignatureRule(ValidationRule):
    """Validate ``compute()`` has exactly (self_state, neighbors) and return annotation."""

    _STATE_NAMES = {"self_state", "state", "s"}
    _NBR_NAMES = {"neighbors", "nbrs", "neighborhood"}

    def check(self, cls: Type) -> List[str]:
        method = getattr(cls, "compute")
        sig = inspect.signature(method)

        params = [p for p in sig.parameters if p != "self"]

        if len(params) != 2:
            raise ValidationError(
                f"{cls.__name__}.compute() must have exactly 2 parameters "
                f"(self_state, neighbors), got {len(params)}"
            )

        if params[0] not in self._STATE_NAMES:
            raise ValidationError(
                f"{cls.__name__}.compute() first parameter should be 'self_state' "
                f"(got '{params[0]}')"
            )

        if params[1] not in self._NBR_NAMES:
            raise ValidationError(
                f"{cls.__name__}.compute() second parameter should be 'neighbors' "
                f"(got '{params[1]}')"
            )

        if sig.return_annotation is inspect.Parameter.empty:
            raise ValidationError(
                f"{cls.__name__}.compute() must have return type annotation"
            )
        return []


class DeprecatedMethodRule(ValidationRule):
    """Warn when obsolete method names are present."""

    _DEPRECATED = {"step": "compute", "update": "compute"}

    def check(self, cls: Type) -> List[str]:
        warnings = []
        for bad_name, good_name in self._DEPRECATED.items():
            if hasattr(cls, bad_name):
                msg = (
                    f"{cls.__name__} defines {bad_name}() "
                    f"but should use {good_name}()"
                )
                _log.warning(msg)
                warnings.append(msg)
        return warnings


# ---------------------------------------------------------------------------
# ValidationPipeline — runs rules in sequence
# ---------------------------------------------------------------------------

class ValidationPipeline:
    """Runs a list of :class:`ValidationRule` instances against a class.

    Rules execute in insertion order.  Any rule may raise
    :class:`ValidationError` to abort the pipeline; non-critical rules
    return warning strings instead.
    """

    def __init__(self, rules: List[ValidationRule] = None) -> None:
        self._rules: List[ValidationRule] = list(rules) if rules else []

    def add_rule(self, rule: ValidationRule) -> "ValidationPipeline":
        """Append a rule and return *self* for chaining."""
        self._rules.append(rule)
        return self

    def run(self, cls: Type) -> List[str]:
        """Run all rules; return aggregated warnings.

        Raises :class:`ValidationError` on the first critical failure.
        """
        warnings: List[str] = []
        for rule in self._rules:
            warnings.extend(rule.check(cls))
        return warnings


# Default pipeline used by AggregateValidator
_DEFAULT_PIPELINE = ValidationPipeline([
    MarkerRule(),
    RequiredMethodsRule(),
    InitialStateRule(),
    ComputeSignatureRule(),
    DeprecatedMethodRule(),
])


# ---------------------------------------------------------------------------
# AggregateValidator — preserved public interface; delegates to pipeline
# ---------------------------------------------------------------------------

class AggregateValidator:
    """Validates aggregate function classes before transpilation.

    Delegates to a :class:`ValidationPipeline` internally so that new rules
    can be added or the pipeline can be replaced without changing call sites.
    """

    REQUIRED_METHODS = ["initial_state", "compute"]
    OPTIONAL_METHODS = ["when_source", "when_merge"]

    _pipeline: ValidationPipeline = _DEFAULT_PIPELINE

    @classmethod
    def set_pipeline(cls, pipeline: ValidationPipeline) -> None:
        """Replace the active validation pipeline (useful for testing)."""
        cls._pipeline = pipeline

    @classmethod
    def reset_pipeline(cls) -> None:
        """Restore the default pipeline."""
        cls._pipeline = _DEFAULT_PIPELINE

    @staticmethod
    def validate(cls: Type) -> List[str]:
        """Validate *cls* using the active pipeline.

        Returns a list of warnings (empty list = valid).
        Raises :class:`ValidationError` on critical failures.
        """
        _log.debug("Validating aggregate class %s", cls.__name__)
        warnings = AggregateValidator._pipeline.run(cls)
        if warnings:
            _log.debug(
                "%s produced %d warning(s): %s",
                cls.__name__, len(warnings), warnings
            )
        return warnings

    @staticmethod
    def get_state_type(cls: Type) -> Type:
        """Extract state type from ``initial_state()`` return annotation."""
        method = getattr(cls, "initial_state")
        sig = inspect.signature(method)

        if sig.return_annotation is inspect.Parameter.empty:
            raise ValidationError(
                f"{cls.__name__}.initial_state() must have return type annotation"
            )

        return sig.return_annotation

    @staticmethod
    def is_supported_type(py_type: Type) -> bool:
        """Return ``True`` when *py_type* can be code-generated."""
        from .types import AggregateType

        try:
            AggregateType.infer(py_type)
            return True
        except ValueError:
            return False

    @staticmethod
    def check_method_signature(method: Any, expected_params: List[str]) -> bool:
        """Return ``True`` when *method* has exactly *expected_params* (excl. self)."""
        sig = inspect.signature(method)
        actual = [p for p in sig.parameters if p != "self"]
        return actual == expected_params
