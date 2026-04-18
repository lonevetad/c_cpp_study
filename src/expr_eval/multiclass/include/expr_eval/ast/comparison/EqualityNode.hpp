#pragma once

#include "expr_eval/ast/BinaryNode.hpp"
#include "expr_eval/config.hpp"
#include "expr_eval/errors.hpp"
#include "expr_eval/types/ValueType.hpp"

#include <format>

namespace ExprEval {

// CRTP base for equality/inequality operators (== / !=).
//
// Derived must provide:
//   static constexpr std::string_view kSymbol           — display symbol
//   static constexpr bool             kHeterogeneousResult — result when types differ
//   static bool compareBool(bool l, bool r)
//   static bool compareNumber(double l, double r)
template<typename Derived>
class EqualityNode : public BinaryNode {
public:
    using BinaryNode::BinaryNode;

    [[nodiscard]] Value evaluate(const Variables& vars) const override final {
        Value l = left_->evaluate(vars);
        Value r = right_->evaluate(vars);
        if (l.type() != r.type()) {
            if constexpr (kAllowHeterogeneousComparisons) {
                return Value{Derived::kHeterogeneousResult};
            } else {
                throw EvaluationError(std::format(
                    "Node (ID: {}) '{}': type mismatch (heterogeneous comparisons disabled)",
                    id, Derived::kSymbol));
            }
        }
        if (l.type() == ValueType::BOOLEAN)
            return Value{Derived::compareBool(l.getBool(), r.getBool())};
        return Value{Derived::compareNumber(l.getNumber(), r.getNumber())};
    }

    void print(std::ostream& out) const override final {
        printBinary(out, Derived::kSymbol);
    }
};

} // namespace ExprEval
