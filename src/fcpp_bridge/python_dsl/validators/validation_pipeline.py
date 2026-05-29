from typing import Type, List

from .validation_rule import ValidationRule


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
