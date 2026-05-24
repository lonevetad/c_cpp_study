from typing import Type, List

from .validation_rule import ValidationRule
from fcpp_bridge.log import get_logger

_log = get_logger(__name__)


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
