#pragma once

#include "expr_eval/ast/UnaryNode.hpp"

namespace ExprEval {

class NotNode final : public UnaryNode {
public:
    using UnaryNode::UnaryNode;

    [[nodiscard]] Value evaluate(const Variables& vars) const override;
    void print(std::ostream& out) const override;

    // Eliminates double-NOT: NOT(NOT(x)) → x
    [[nodiscard]] std::unique_ptr<AstNode> optimize(std::unique_ptr<AstNode> self) override;
};

} // namespace ExprEval
