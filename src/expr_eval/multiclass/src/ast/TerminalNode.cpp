#include "expr_eval/ast/TerminalNode.hpp"
#include "expr_eval/errors.hpp"

#include <format>

namespace ExprEval {

Value TerminalNode::evaluate(const Variables& vars) const {
    if (auto v = Value::fromString(value_)) return *v;
    auto it = vars.find(value_);
    if (it == vars.end())
        throw EvaluationError(std::format("Unknown variable: {}", value_));
    if (auto v = Value::fromString(it->second)) return *v;
    throw EvaluationError(
        std::format("Variable '{}' has non-literal value: {}", value_, it->second));
}

void TerminalNode::print(std::ostream& out) const {
    printTabs(out, depth);
    out << "T: (d.: " << depth << " ; ID: " << id << ") : " << value_ << "\n";
}

} // namespace ExprEval
