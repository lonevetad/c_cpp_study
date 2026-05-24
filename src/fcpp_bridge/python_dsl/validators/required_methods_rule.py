from typing import Type, List

from .validation_error import ValidationError
from .validation_rule import ValidationRule


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
