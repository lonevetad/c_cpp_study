from typing import Type, List

from .validation_error import ValidationError
from .validation_rule import ValidationRule


class MarkerRule(ValidationRule):
    """Require the ``_is_aggregate_function`` marker set by the decorator."""

    def check(self, cls: Type) -> List[str]:
        if not getattr(cls, "_is_aggregate_function", False):
            raise ValidationError(
                f"{cls.__name__} is not decorated with @aggregate_function"
            )
        return []
