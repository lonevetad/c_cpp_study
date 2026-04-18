#pragma once

#include "expr_eval/ast/AstNode.hpp"

#include <memory>
#include <string_view>

namespace ExprEval {

class BinaryNode : public AstNode {
public:
    BinaryNode(std::unique_ptr<AstNode> left, std::unique_ptr<AstNode> right) noexcept
        : left_(std::move(left)), right_(std::move(right)) {}

    void adjustDepthRecursive(int delta) noexcept override {
        depth += delta;
        if (left_)  left_->adjustDepthRecursive(delta);
        if (right_) right_->adjustDepthRecursive(delta);
    }

    // Default: recursively optimize both children, return self.
    [[nodiscard]] std::unique_ptr<AstNode> optimize(std::unique_ptr<AstNode> self) override;

protected:
    std::unique_ptr<AstNode> left_;
    std::unique_ptr<AstNode> right_;

    void printBinary(std::ostream& out, std::string_view symbol) const;
};

} // namespace ExprEval
