#pragma once

#include "expr_eval/ast/comparison/OrderComparisonNode.hpp"

namespace ExprEval {

class GtNode final : public OrderComparisonNode<GtNode> {
public:
    using OrderComparisonNode<GtNode>::OrderComparisonNode;
    static constexpr std::string_view kSymbol = ">";
    static bool compare(double l, double r) { return l > r; }
};

} // namespace ExprEval
