#pragma once

#include "expr_eval/ast/AstNode.hpp"

#include <memory>

namespace ExprEval {

class UnaryNode : public AstNode {
public:
    explicit UnaryNode(std::unique_ptr<AstNode> child) noexcept
        : child_(std::move(child)) {}

    void adjustDepthRecursive(int delta) noexcept override {
        depth += delta;
        if (child_) child_->adjustDepthRecursive(delta);
    }

    // Default: optimize child, return self. Override for structural reductions.
    [[nodiscard]] std::unique_ptr<AstNode> optimize(std::unique_ptr<AstNode> self) override;

protected:
    std::unique_ptr<AstNode> child_;
};

} // namespace ExprEval
