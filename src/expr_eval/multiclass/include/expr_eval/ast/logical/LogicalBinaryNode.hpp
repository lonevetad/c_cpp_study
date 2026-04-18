#pragma once

#include "expr_eval/ast/BinaryNode.hpp"
#include "expr_eval/errors.hpp"
#include "expr_eval/types/ValueType.hpp"

#include <format>

namespace ExprEval {

// CRTP base for short-circuiting binary logical operators (AND / OR).
//
// Derived must provide:
//   static constexpr bool        kShortCircuitValue  — the value that stops evaluation
//   static constexpr std::string_view kSymbol        — display symbol ("&&" / "||")
template<typename Derived>
class LogicalBinaryNode : public BinaryNode {
public:
    using BinaryNode::BinaryNode;

    [[nodiscard]] Value evaluate(const Variables& vars) const override final {
        Value l = left_->evaluate(vars);
        if (l.type() != ValueType::BOOLEAN)
            throw EvaluationError(std::format(
                "Node (ID: {}) '{}' expects BOOLEAN left operand", id, Derived::kSymbol));
        if (l.getBool() == Derived::kShortCircuitValue)
            return Value{Derived::kShortCircuitValue};
        Value r = right_->evaluate(vars);
        if (r.type() != ValueType::BOOLEAN)
            throw EvaluationError(std::format(
                "Node (ID: {}) '{}' expects BOOLEAN right operand", id, Derived::kSymbol));
        return r;
    }

    void print(std::ostream& out) const override final {
        printBinary(out, Derived::kSymbol);
    }
};

} // namespace ExprEval
