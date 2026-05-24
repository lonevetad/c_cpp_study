from abc import ABC, abstractmethod
from typing import Type, List

from .validation_error import ValidationError


class ValidationRule(ABC):
    """Abstract base for a single validation rule.

    ``check()`` returns a list of warning strings (empty = passed).
    Implementations raise :class:`ValidationError` for critical failures.
    """

    @abstractmethod
    def check(self, cls: Type) -> List[str]:
        """Validate *cls* and return warnings.  Raise ValidationError on failure."""
        ...
