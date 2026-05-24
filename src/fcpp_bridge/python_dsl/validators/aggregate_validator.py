import inspect
from typing import Any, Type, List

from .validation_error import ValidationError
from .validation_pipeline import ValidationPipeline
from .marker_rule import MarkerRule
from .required_methods_rule import RequiredMethodsRule
from .initial_state_rule import InitialStateRule
from .compute_signature_rule import ComputeSignatureRule
from .deprecated_method_rule import DeprecatedMethodRule
from fcpp_bridge.log import get_logger

_log = get_logger(__name__)

_DEFAULT_PIPELINE = ValidationPipeline([
    MarkerRule(),
    RequiredMethodsRule(),
    InitialStateRule(),
    ComputeSignatureRule(),
    DeprecatedMethodRule(),
])


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
        from fcpp_bridge.python_dsl.types import AggregateType

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
