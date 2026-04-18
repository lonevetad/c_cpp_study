#include "expr_eval/parser/Parser.hpp"

#include "expr_eval/ast/ExprNode.hpp"
#include "expr_eval/ast/TerminalNode.hpp"
#include "expr_eval/ast/arithmetic/NegateNode.hpp"
#include "expr_eval/ast/comparison/EqNode.hpp"
#include "expr_eval/ast/comparison/GtNode.hpp"
#include "expr_eval/ast/comparison/GteNode.hpp"
#include "expr_eval/ast/comparison/LtNode.hpp"
#include "expr_eval/ast/comparison/LteNode.hpp"
#include "expr_eval/ast/comparison/NeqNode.hpp"
#include "expr_eval/ast/logical/AndNode.hpp"
#include "expr_eval/ast/logical/NotNode.hpp"
#include "expr_eval/ast/logical/OrNode.hpp"
#include "expr_eval/config.hpp"
#include "expr_eval/errors.hpp"

#include <format>

namespace ExprEval {

// ── helpers ──────────────────────────────────────────────────────────────────

void Parser::skipWhitespace() noexcept {
    while (!atEnd() && (current() == ' ' || current() == '\t' || current() == '\n'))
        ++index_;
}

void Parser::checkEnd() const {
    if (atEnd())
        throw ParseError(
            std::format("Unexpected end of expression at index {}: {}", index_, expression_));
}

void Parser::checkDepth(int depth) const {
    if (depth > kMaxRecursionDepth)
        throw ParseError(
            std::format("Recursion depth ({}) exceeded in: {}", depth, expression_));
}

std::string Parser::extractTerminalValue() {
    std::size_t start = index_;
    while (!atEnd() && !kUnallowedCharsTerminal[static_cast<unsigned char>(current())])
        ++index_;
    if (index_ == start)
        throw ParseError(
            std::format("Expected terminal value at index {} in: {}", index_, expression_));
    return expression_.substr(start, index_ - start);
}

// ── public entry point ────────────────────────────────────────────────────────

std::unique_ptr<AstNode> Parser::parse() {
    return parseOr(0);
}

// ── recursive-descent levels ──────────────────────────────────────────────────

std::unique_ptr<AstNode> Parser::parseOr(int depth) {
    checkDepth(depth);
    checkEnd();
    auto left = parseAnd(depth);
    skipWhitespace();
    if (atEnd() || !hasLookahead() || current() != '|' || lookahead() != '|')
        return left;

    left->adjustDepthRecursive(1);
    index_ += 2;
    skipWhitespace();
    checkEnd();

    auto right = parseOr(depth + 1);
    auto node  = std::make_unique<OrNode>(std::move(left), std::move(right));
    node->depth = depth;
    node->id    = nextId_++;
    return node;
}

std::unique_ptr<AstNode> Parser::parseAnd(int depth) {
    checkDepth(depth);
    checkEnd();
    auto left = parseEqual(depth);
    skipWhitespace();
    if (atEnd() || !hasLookahead() || current() != '&' || lookahead() != '&')
        return left;

    left->adjustDepthRecursive(1);
    index_ += 2;
    skipWhitespace();
    checkEnd();

    auto right = parseAnd(depth + 1);
    auto node  = std::make_unique<AndNode>(std::move(left), std::move(right));
    node->depth = depth;
    node->id    = nextId_++;
    return node;
}

std::unique_ptr<AstNode> Parser::parseEqual(int depth) {
    checkDepth(depth);
    checkEnd();
    auto left = parseNumericComparison(depth);
    skipWhitespace();
    bool isEq  = hasLookahead() && current() == '=' && lookahead() == '=';
    bool isNeq = hasLookahead() && current() == '!' && lookahead() == '=';
    if (!isEq && !isNeq)
        return left;

    left->adjustDepthRecursive(1);
    index_ += 2;
    skipWhitespace();
    checkEnd();

    auto right = parseEqual(depth + 1);
    std::unique_ptr<AstNode> node;
    if (isEq)
        node = std::make_unique<EqNode>(std::move(left), std::move(right));
    else
        node = std::make_unique<NeqNode>(std::move(left), std::move(right));
    node->depth = depth;
    node->id    = nextId_++;
    return node;
}

std::unique_ptr<AstNode> Parser::parseNumericComparison(int depth) {
    checkDepth(depth);
    checkEnd();
    auto left = parseNot(depth);
    skipWhitespace();
    if (atEnd() || (current() != '<' && current() != '>'))
        return left;

    left->adjustDepthRecursive(1);
    bool isGt = (current() == '>');
    ++index_;
    checkEnd();
    bool isEq = (current() == '=');
    if (isEq) ++index_;
    skipWhitespace();
    checkEnd();

    auto right = parseNot(depth + 1);
    std::unique_ptr<AstNode> node;
    if (isGt && isEq)       node = std::make_unique<GteNode>(std::move(left), std::move(right));
    else if (isGt)          node = std::make_unique<GtNode>(std::move(left), std::move(right));
    else if (isEq)          node = std::make_unique<LteNode>(std::move(left), std::move(right));
    else                    node = std::make_unique<LtNode>(std::move(left), std::move(right));
    node->depth = depth;
    node->id    = nextId_++;
    return node;
}

std::unique_ptr<AstNode> Parser::parseNot(int depth) {
    checkDepth(depth);
    checkEnd();
    if (current() != '!')
        return parseNegate(depth);

    ++index_;
    skipWhitespace();
    checkEnd();
    auto child = parseNot(depth + 1);
    auto node  = std::make_unique<NotNode>(std::move(child));
    node->depth = depth;
    node->id    = nextId_++;
    return node;
}

std::unique_ptr<AstNode> Parser::parseNegate(int depth) {
    checkDepth(depth);
    checkEnd();
    if (current() != '-')
        return parseExpr(depth);

    ++index_;
    skipWhitespace();
    checkEnd();
    auto child = parseNegate(depth + 1);
    auto node  = std::make_unique<NegateNode>(std::move(child));
    node->depth = depth;
    node->id    = nextId_++;
    return node;
}

std::unique_ptr<AstNode> Parser::parseExpr(int depth) {
    checkDepth(depth);
    checkEnd();
    if (current() != '(')
        return parseTerminal(depth);

    ++index_;
    skipWhitespace();
    checkEnd();
    auto inner = parseOr(depth + 1);
    checkEnd();
    if (current() != ')')
        throw ParseError(std::format("Missing ')' at index {}", index_));
    ++index_;
    skipWhitespace();

    auto node  = std::make_unique<ExprNode>(std::move(inner));
    node->depth = depth;
    node->id    = nextId_++;
    return node;
}

std::unique_ptr<AstNode> Parser::parseTerminal(int depth) {
    skipWhitespace();
    checkEnd();
    if (current() == '(')
        return parseExpr(depth);

    auto val  = extractTerminalValue();
    auto node = std::make_unique<TerminalNode>(std::move(val));
    node->depth = depth;
    node->id    = nextId_++;
    return node;
}

} // namespace ExprEval
