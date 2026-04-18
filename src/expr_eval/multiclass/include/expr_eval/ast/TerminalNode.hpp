#pragma once

#include "expr_eval/ast/AstNode.hpp"

#include <string>

namespace ExprEval {

class TerminalNode final : public AstNode {
public:
    explicit TerminalNode(std::string value) noexcept : value_(std::move(value)) {}

    [[nodiscard]] Value evaluate(const Variables& vars) const override;
    void print(std::ostream& out) const override;

    [[nodiscard]] std::unique_ptr<AstNode> optimize(std::unique_ptr<AstNode> self) override {
        return self;
    }

private:
    std::string value_;
};

} // namespace ExprEval
