#pragma once

#include "expr_eval/ast/AstNode.hpp"

#include <memory>
#include <string>

namespace ExprEval {

class Parser {
public:
    explicit Parser(std::string expression) noexcept : expression_(std::move(expression)) {}

    [[nodiscard]] std::unique_ptr<AstNode> parse();

private:
    std::string expression_;
    std::size_t index_{};
    int         nextId_{};

    // Recursive-descent levels (operator precedence, lowest to highest):
    [[nodiscard]] std::unique_ptr<AstNode> parseOr(int depth);
    [[nodiscard]] std::unique_ptr<AstNode> parseAnd(int depth);
    [[nodiscard]] std::unique_ptr<AstNode> parseEqual(int depth);
    [[nodiscard]] std::unique_ptr<AstNode> parseNumericComparison(int depth);
    [[nodiscard]] std::unique_ptr<AstNode> parseNot(int depth);
    [[nodiscard]] std::unique_ptr<AstNode> parseNegate(int depth);
    [[nodiscard]] std::unique_ptr<AstNode> parseExpr(int depth);
    [[nodiscard]] std::unique_ptr<AstNode> parseTerminal(int depth);
    [[nodiscard]] std::string              extractTerminalValue();

    void skipWhitespace() noexcept;
    void checkEnd() const;
    void checkDepth(int depth) const;

    [[nodiscard]] bool atEnd() const noexcept { return index_ >= expression_.size(); }
    [[nodiscard]] char current() const noexcept { return expression_[index_]; }
    [[nodiscard]] bool hasLookahead() const noexcept { return index_ + 1 < expression_.size(); }
    [[nodiscard]] char lookahead() const noexcept { return expression_[index_ + 1]; }
};

} // namespace ExprEval
