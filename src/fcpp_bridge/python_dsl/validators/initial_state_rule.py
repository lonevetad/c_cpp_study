import inspect
from typing import Type, List

from .validation_error import ValidationError
from .validation_rule import ValidationRule


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
