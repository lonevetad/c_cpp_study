#pragma once

#include "expr_eval/types/Variables.hpp"

#include <string_view>

namespace ExprEval {

// Parses and evaluates a boolean expression string.
// Variables are resolved through `variables` (string → string, parsed as bool/double).
// Throws ParseError on malformed input; EvaluationError on type mismatches.
[[nodiscard]] bool evaluate(std::string_view expression, const Variables& variables);

} // namespace ExprEval
