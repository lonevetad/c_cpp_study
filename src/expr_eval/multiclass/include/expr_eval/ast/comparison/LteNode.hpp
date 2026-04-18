#pragma once

#include "expr_eval/ast/comparison/OrderComparisonNode.hpp"

namespace ExprEval {

class LteNode final : public OrderComparisonNode<LteNode> {
public:
    using OrderComparisonNode<LteNode>::OrderComparisonNode;
    static constexpr std::string_view kSymbol = "<=";
    static bool compare(double l, double r) { return l <= r; }
};

} // namespace ExprEval
