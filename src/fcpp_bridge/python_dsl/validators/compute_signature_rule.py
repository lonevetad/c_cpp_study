import inspect
from typing import Type, List

from .validation_error import ValidationError
from .validation_rule import ValidationRule


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
