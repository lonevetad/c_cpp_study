#include "expr_eval/ExpressionEvaluator.hpp"

#include "expr_eval/ast/AstNode.hpp"
#include "expr_eval/errors.hpp"
#include "expr_eval/parser/Parser.hpp"
#include "expr_eval/types/ValueType.hpp"

#include <format>
#include <iostream>

namespace ExprEval {

bool evaluate(std::string_view expression, const Variables& variables) {
    std::cout << "\n\nParsing: " << expression << "\n";

    Parser parser{std::string{expression}};
    auto root = parser.parse();
    root = optimizeNode(std::move(root));

    std::cout << "PARSED TREE:\n";
    root->print(std::cout);

    Value result = root->evaluate(variables);
    if (result.type() != ValueType::BOOLEAN)
        throw EvaluationError(
            std::format("Expression '{}' did not evaluate to BOOLEAN", expression));

    return result.getBool();
}

} // namespace ExprEval
