#pragma once

#include "expr_eval/ast/comparison/OrderComparisonNode.hpp"

namespace ExprEval {

class GteNode final : public OrderComparisonNode<GteNode> {
public:
    using OrderComparisonNode<GteNode>::OrderComparisonNode;
    static constexpr std::string_view kSymbol = ">=";
    static bool compare(double l, double r) { return l >= r; }
};

} // namespace ExprEval
