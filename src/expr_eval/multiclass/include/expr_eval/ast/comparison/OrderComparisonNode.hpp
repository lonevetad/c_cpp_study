#pragma once

#include "expr_eval/ast/BinaryNode.hpp"
#include "expr_eval/errors.hpp"
#include "expr_eval/types/ValueType.hpp"

#include <format>

namespace ExprEval {

// CRTP base for ordered numeric comparisons (< <= > >=).
//
// Derived must provide:
//   static constexpr std::string_view kSymbol  — display symbol
//   static bool compare(double l, double r)    — the actual comparison
template<typename Derived>
class OrderComparisonNode : public BinaryNode {
public:
    using BinaryNode::BinaryNode;

    [[nodiscard]] Value evaluate(const Variables& vars) const override final {
        Value l = left_->evaluate(vars);
        Value r = right_->evaluate(vars);
        if (l.type() != ValueType::NUMBER || r.type() != ValueType::NUMBER)
            throw EvaluationError(std::format(
                "Node (ID: {}) '{}' requires two NUMBER operands", id, Derived::kSymbol));
        return Value{Derived::compare(l.getNumber(), r.getNumber())};
    }

    void print(std::ostream& out) const override final {
        printBinary(out, Derived::kSymbol);
    }
};

} // namespace ExprEval
