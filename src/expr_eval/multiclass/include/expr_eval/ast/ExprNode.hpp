#pragma once

#include "expr_eval/ast/UnaryNode.hpp"

namespace ExprEval {

// Parenthesised sub-expression. Collapsed (inlined) during optimisation.
class ExprNode final : public UnaryNode {
public:
    using UnaryNode::UnaryNode;

    [[nodiscard]] Value evaluate(const Variables& vars) const override;
    void print(std::ostream& out) const override;

    // Collapses self: returns child after adjusting depths, recursing on the result.
    [[nodiscard]] std::unique_ptr<AstNode> optimize(std::unique_ptr<AstNode> self) override;
};

} // namespace ExprEval
