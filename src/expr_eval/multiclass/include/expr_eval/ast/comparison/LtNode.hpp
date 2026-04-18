#pragma once

#include "expr_eval/ast/comparison/OrderComparisonNode.hpp"

namespace ExprEval {

class LtNode final : public OrderComparisonNode<LtNode> {
public:
    using OrderComparisonNode<LtNode>::OrderComparisonNode;
    static constexpr std::string_view kSymbol = "<";
    static bool compare(double l, double r) { return l < r; }
};

} // namespace ExprEval
