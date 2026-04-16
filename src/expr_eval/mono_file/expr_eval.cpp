#include <iostream>
#include <stdio.h>
#include <stdexcept>
#include <string>
#include <map>
#include <array>

#define MAX_RECURSION_DEPTH 10000

#define ALLOW_ETHEROGENEOUS_COMPARISONS true // if true, then numeric and boolean comparisons are allowed BUT statically evaluated to true/false

namespace ExpressionsEvaluator
{
    /*
    A compile-time character lookup tables seems faster than either a cascading chaing of comparisons in OR or an actual std::set<char> membership check
    */
    inline constexpr std::array<bool, 256> UNALLOWED_CHARS_TERMINAL = []()
    {
        std::array<bool, 256> result{};
        constexpr std::array chars{' ', '\t', '\n', '(', ')', '!', '&', '|', '=', '<', '>', ',', '+', '-', '*', '/', '\'', '\"', '\\', '#', '@', '[', ']', '{', '}', ';', ':', '?', '^', '%', '~', '`'}; // add more if needed
        for (char c : chars)
        {
            result[static_cast<unsigned char>(c)] = true;
        }
        return result;
    }();

    /**
     * Technically, "EXPR"(-ession) is not an operator and "TERMINAL" is a "leaf" node
     */
    enum class Operators
    {
        AND,
        OR,
        EQ,
        NEQ,
        LT,
        LTE,
        GT,
        GTE,
        NOT,
        /*SUM, SUBTRACT, MULTIPLY, DIVIDE,*/
        NEGATE,
        EXPR,
        TERMINAL
    };

    enum class ValueType
    {
        UNKNOWN,
        BOOLEAN,
        NUMBER /* double, actually */
    };

    struct ParserNode
    {
        Operators op{Operators::EXPR};
        // ValueType valueType; removed because it's unused in this particular parsing context
        int depth;
        int id;
        std::string *value; /* only for TERMINAL */
        ParserNode *left;   /* only for non-TERMINAL */
        ParserNode *right;  /* only for non-TERMINAL */

        ParserNode(Operators o, std::string *v) : op(o), depth(0), id(0), value(v), left(nullptr), right(nullptr) {}
    };

    struct EvaluationContext
    {
        ValueType resultType;
        union
        {
            bool boolValue;
            double numberValue;
        } result;
    };

    struct ParserContext
    {
        int index;
        int progressiveID;
        std::string &expression;

        ParserContext(std::string &e) : index(0), progressiveID(0), expression(e) {}

        bool is_white(char c) const
        {
            return c == ' ' || c == '\n' || c == '\t';
        }

        bool is_unallowed(char c) const
        {
            return UNALLOWED_CHARS_TERMINAL[static_cast<unsigned char>(c)];
        }
    };

    // cleanup functions

    static void deleteTree(ParserNode *node)
    {
        if (node)
        {
            delete node->value;
            deleteTree(node->left);
            deleteTree(node->right);
            delete node;
        }
    }

    // parser node functions

    static void alterDepth(ParserNode *node, int delta, bool evenMyself)
    {
        if (evenMyself)
        {
            node->depth += delta;
        }
        if (node->left != nullptr)
        {
            alterDepth(node->left, delta, true);
        }
        if (node->right != nullptr)
        {
            alterDepth(node->right, delta, true);
        }
    }
    static void alterDepth(ParserNode *node, int delta)
    {
        alterDepth(node, delta, true);
    }

    static ParserNode *optimize(ParserNode *node)
    {
        if (node->op == Operators::EXPR && node->left != nullptr)
        {
            ParserNode *subExpr = node->left;
            node->op = subExpr->op;
            node->value = subExpr->value;
            node->right = subExpr->right;
            node->left = subExpr->left;
            node->id = subExpr->id;
            delete subExpr;
            alterDepth(node, -1, false);
            return optimize(node); // should I optimize again?
        }
        if (
            // self-inverse operators
            (node->op == Operators::NOT || node->op == Operators::NEGATE) &&
            node->left != nullptr && node->left->op == node->op)
        {
            ParserNode *notNode = node->left;
            ParserNode *deeperNotNode = notNode->left;
            node->op = deeperNotNode->op;
            node->value = deeperNotNode->value;
            node->right = deeperNotNode->right;
            node->left = deeperNotNode->left;
            node->id = deeperNotNode->id;
            delete deeperNotNode;
            delete notNode;
            alterDepth(node, -2, false);
            return optimize(node); // should I optimize again?
        }
        if (node->left != nullptr)
        {
            optimize(node->left);
        }
        if (node->right != nullptr)
        {
            optimize(node->right);
        }
        return node;
    }
    static void addTabs(std::ostream &out, int d)
    {
        while (d-- > 0)
        {
            out << "  ";
        }
    }

    static void printTree(std::ostream &out, ParserNode *node)
    {
        if (node == nullptr)
        {
            out << "NULL NODE (should not happen)" << std::endl;
            return;
        }
        switch (node->op)
        {
        case Operators::AND:
            printTree(out, node->left);
            addTabs(out, node->depth);
            out << "&& (d.: " << node->depth << " ; ID: " << node->id << ")" << std::endl;
            printTree(out, node->right);
            break;
        case Operators::OR:
            printTree(out, node->left);
            addTabs(out, node->depth);
            out << "|| (d.: " << node->depth << " ; ID: " << node->id << ")" << std::endl;
            printTree(out, node->right);
            break;
        case Operators::NOT:
            addTabs(out, node->depth);
            out << "! (d.: " << node->depth << " ; ID: " << node->id << ")" << std::endl;
            printTree(out, node->left);
            break;
        case Operators::NEGATE:
            addTabs(out, node->depth);
            out << "- (d.: " << node->depth << " ; ID: " << node->id << ")" << std::endl;
            printTree(out, node->left);
            break;
        case Operators::EQ:
            printTree(out, node->left);
            addTabs(out, node->depth);
            out << "== (d.: " << node->depth << " ; ID: " << node->id << ")" << std::endl;
            printTree(out, node->right);
            break;
        case Operators::NEQ:
            printTree(out, node->left);
            addTabs(out, node->depth);
            out << "!= (d.: " << node->depth << " ; ID: " << node->id << ")" << std::endl;
            printTree(out, node->right);
            break;
        case Operators::LT:
            printTree(out, node->left);
            addTabs(out, node->depth);
            out << "< (d.: " << node->depth << " ; ID: " << node->id << ")" << std::endl;
            printTree(out, node->right);
            break;
        case Operators::GT:
            printTree(out, node->left);
            addTabs(out, node->depth);
            out << "> (d.: " << node->depth << " ; ID: " << node->id << ")" << std::endl;
            printTree(out, node->right);
            break;
        case Operators::LTE:
            printTree(out, node->left);
            addTabs(out, node->depth);
            out << "<= (d.: " << node->depth << " ; ID: " << node->id << ")" << std::endl;
            printTree(out, node->right);
            break;
        case Operators::GTE:
            printTree(out, node->left);
            addTabs(out, node->depth);
            out << ">= (d.: " << node->depth << " ; ID: " << node->id << ")" << std::endl;
            printTree(out, node->right);
            break;
        case Operators::EXPR:
            addTabs(out, node->depth);
            out << "( (d.: " << node->depth << " ; ID: " << node->id << ")" << std::endl;
            printTree(out, node->left);
            addTabs(out, node->depth);
            out << ")" << std::endl;
            break;
        case Operators::TERMINAL:
            addTabs(out, node->depth);
            out << "T: (d.: " << node->depth << " ; ID: " << node->id << ") : " << *node->value << std::endl;
            break;
        }
    }

    // helper functions

    static void checkRecursionDepth(int depth, const std::string &expression)
    {
        if (depth > MAX_RECURSION_DEPTH)
        {
            throw std::runtime_error(
                std::format("Recursion depth ({}) exceeded in: {}", depth, expression));
        }
    }

    static void checkEndOfExpression(ParserContext &ctx, ParserNode *currentNode)
    {
        if ((unsigned)ctx.index >= ctx.expression.length())
        {
            if (currentNode != nullptr)
            {
                deleteTree(currentNode); // free the memory
            }
            throw std::runtime_error(
                std::format("END OF EXPRESSION: {} ; at index {}", ctx.expression, ctx.index));
        }
    }

    static void skipWhiteChars(ParserContext &ctx)
    {
        int len = (int)ctx.expression.length();
        while (ctx.index < len && ctx.is_white(ctx.expression[ctx.index]))
        {
            ctx.index++;
        }
    }

    // PARSING

    static ParserNode *parseOr(ParserContext &ctx, int depth);
    static ParserNode *parseOr(ParserNode *left, ParserContext &ctx, int depth);
    static ParserNode *parseAnd(ParserContext &ctx, int depth);
    static ParserNode *parseAnd(ParserNode *left, ParserContext &ctx, int depth);
    static ParserNode *parseEqual(ParserContext &ctx, int depth);
    static ParserNode *parseEqual(ParserNode *left, ParserContext &ctx, int depth);
    static ParserNode *parseNumericComparison(ParserContext &ctx, int depth);                   // then / equal
    static ParserNode *parseNumericComparison(ParserNode *left, ParserContext &ctx, int depth); // then / equal
    static ParserNode *parseNot(ParserContext &ctx, int depth);
    static ParserNode *parseNegate(ParserContext &ctx, int depth);
    static ParserNode *parseExpr(ParserContext &ctx, int depth);
    static ParserNode *parseTerminal(ParserContext &ctx, int depth);

    static ParserNode *parseOr(ParserContext &ctx, int depth)
    {
        return parseOr(nullptr, ctx, depth);
    }
    static ParserNode *parseOr(ParserNode *left, ParserContext &ctx, int depth)
    {
        checkRecursionDepth(depth, ctx.expression);
        if (!left)
        {
            checkEndOfExpression(ctx, nullptr);
            left = parseAnd(ctx, depth);
            skipWhiteChars(ctx);
            if ((unsigned)ctx.index >= (ctx.expression.length() - 1) || ctx.expression[ctx.index] != '|' || ctx.expression[ctx.index + 1] != '|')
            {
                return left; // no OR to be consumed -> expression fully evaluated
            }
        }
        alterDepth(left, 1); // this is not a simple expression, but an OR: so the "left" is deeper than the current one
        ctx.index += 2;      // consume the OR
        skipWhiteChars(ctx);
        checkEndOfExpression(ctx, left);
        ParserNode *orNode = new ParserNode(Operators::OR, nullptr);
        orNode->depth = depth;
        orNode->left = left;
        orNode->id = ctx.progressiveID++;
        try
        {
            orNode->right = parseOr(ctx, depth + 1); // is there another OR in a chain? anway, we can't lower the expression level
        }
        catch (const std::runtime_error &e)
        {
            deleteTree(orNode);
            throw e;
        }
        return orNode;
    }

    static ParserNode *parseAnd(ParserContext &ctx, int depth)
    {
        return parseAnd(nullptr, ctx, depth);
    }
    static ParserNode *parseAnd(ParserNode *left, ParserContext &ctx, int depth)
    {
        checkRecursionDepth(depth, ctx.expression);
        if (!left)
        {
            checkEndOfExpression(ctx, nullptr);
            left = parseEqual(ctx, depth);
            skipWhiteChars(ctx);
            if ((unsigned)ctx.index >= (ctx.expression.length() - 1) || ctx.expression[ctx.index] != '&' || ctx.expression[ctx.index + 1] != '&')
            {
                return left; // no AND to be consumed -> expression fully evaluated
            }
        }
        alterDepth(left, 1); // this is not a simple expression, but an AND: so the "left" is deeper than the current one
        ctx.index += 2;      // consume the AND
        skipWhiteChars(ctx);
        checkEndOfExpression(ctx, left);
        ParserNode *andNode = new ParserNode(Operators::AND, nullptr);
        andNode->depth = depth;
        andNode->left = left;
        andNode->id = ctx.progressiveID++;
        try
        {
            andNode->right = parseAnd(ctx, depth + 1); // is there another AND in a chain? anway, we can't lower the expression level
        }
        catch (const std::runtime_error &e)
        {
            deleteTree(andNode);
            throw e;
        }
        return andNode;
    }

    static ParserNode *parseEqual(ParserContext &ctx, int depth)
    {
        return parseEqual(nullptr, ctx, depth);
    }
    static ParserNode *parseEqual(ParserNode *left, ParserContext &ctx, int depth)
    {
        checkRecursionDepth(depth, ctx.expression);
        if (!left)
        {
            checkEndOfExpression(ctx, nullptr);
            left = parseNumericComparison(ctx, depth);
            skipWhiteChars(ctx);
            if (
                (unsigned)ctx.index >= (ctx.expression.length() - 1) ||
                (ctx.expression[ctx.index] != '=' && ctx.expression[ctx.index] != '!') || ctx.expression[ctx.index + 1] != '=')
            {
                return left; // no EQUAL to be consumed -> expression fully evaluated
            }
        }
        alterDepth(left, 1); // this is not a simple expression, but an AND: so the "left" is deeper than the current one
        bool isEqual = ctx.expression[ctx.index] == '=';
        ctx.index += 2; // consume the EQUAL
        skipWhiteChars(ctx);
        checkEndOfExpression(ctx, left);
        ParserNode *eqNode = new ParserNode(isEqual ? Operators::EQ : Operators::NEQ, nullptr);
        eqNode->depth = depth;
        eqNode->left = left;
        eqNode->id = ctx.progressiveID++;
        try
        {
            eqNode->right = parseEqual(ctx, depth + 1); // associativity of equality -> can chain equalities
        }
        catch (const std::runtime_error &e)
        {
            deleteTree(eqNode);
            throw e;
        }
        return eqNode;
    }

    static ParserNode *parseNumericComparison(ParserContext &ctx, int depth)
    {
        return parseNumericComparison(nullptr, ctx, depth);
    }
    static ParserNode *parseNumericComparison(ParserNode *left, ParserContext &ctx, int depth)
    {
        checkRecursionDepth(depth, ctx.expression);
        checkEndOfExpression(ctx, left);
        int len = ctx.expression.length();
        if (!left)
        {
            left = parseNot(ctx, depth);
            skipWhiteChars(ctx);
            if (
                ctx.index >= (len - 1) ||
                (ctx.expression[ctx.index] != '<' && ctx.expression[ctx.index] != '>'))
            {
                return left; // no comparison to be consumed -> expression fully evaluated
            }
        }
        alterDepth(left, 1); // this is not a simple expression, but an AND: so the "left" is deeper than the current one
        bool isGT = ctx.expression[ctx.index] == '>';
        bool isEqual = false; // hypotesis
        ctx.index++;          // consume the GT/LT
        checkEndOfExpression(ctx, left);
        if (ctx.expression[ctx.index] == '=')
        {
            isEqual = true;
            ctx.index++; // consume the EQUAL
        }
        skipWhiteChars(ctx);
        checkEndOfExpression(ctx, left);
        ParserNode *comparisonNode = new ParserNode(     //
            isEqual ?                                    //
                (isGT ? Operators::GTE : Operators::LTE) //
                    :                                    //
                (isGT ? Operators::GT : Operators::LT),  //
            nullptr                                      //
        );
        comparisonNode->depth = depth;
        comparisonNode->left = left;
        comparisonNode->id = ctx.progressiveID++;
        try
        {
            comparisonNode->right = parseNot(ctx, depth + 1); // disequalities are NOT associative in general -> the right term MUST be a simple expression (or sub-expression)
        }
        catch (const std::runtime_error &e)
        {
            deleteTree(comparisonNode);
            throw e;
        }
        return comparisonNode;
    }

    static ParserNode *parseNot(ParserContext &ctx, int depth)
    {
        checkRecursionDepth(depth, ctx.expression);
        checkEndOfExpression(ctx, nullptr);
        if (ctx.expression[ctx.index] == '!')
        {
            ctx.index++; // consume the NOT
            skipWhiteChars(ctx);
            checkEndOfExpression(ctx, nullptr);
            ParserNode *notNode = new ParserNode(Operators::NOT, nullptr);
            notNode->depth = depth;
            notNode->id = ctx.progressiveID++;
            try
            {
                notNode->left = parseNot(ctx, depth + 1); // NOT is right-associative -> can chain
            }
            catch (const std::runtime_error &e)
            {
                deleteTree(notNode);
                throw e;
            }
            return notNode;
        }
        return parseNegate(ctx, depth);
    }

    static ParserNode *parseNegate(ParserContext &ctx, int depth)
    {
        checkRecursionDepth(depth, ctx.expression);
        checkEndOfExpression(ctx, nullptr);
        if (ctx.expression[ctx.index] == '-')
        {
            ctx.index++; // consume the NEGATE
            skipWhiteChars(ctx);
            checkEndOfExpression(ctx, nullptr);
            ParserNode *negateNode = new ParserNode(Operators::NEGATE, nullptr);
            negateNode->depth = depth;
            negateNode->id = ctx.progressiveID++;
            try
            {
                negateNode->left = parseNegate(ctx, depth + 1); // NEGATE is right-associative -> can chain
            }
            catch (const std::runtime_error &e)
            {
                deleteTree(negateNode);
                throw e;
            }
            return negateNode;
        }
        return parseExpr(ctx, depth);
    }

    static ParserNode *parseExpr(ParserContext &ctx, int depth)
    {
        checkRecursionDepth(depth, ctx.expression);
        checkEndOfExpression(ctx, nullptr);
        if (ctx.expression[ctx.index] == '(')
        {
            ctx.index++; // consume the LEFT PARENTHESIS
            skipWhiteChars(ctx);
            checkEndOfExpression(ctx, nullptr);
            ParserNode *exprNode = new ParserNode(Operators::EXPR, nullptr);
            exprNode->depth = depth;
            exprNode->id = ctx.progressiveID++;
            try
            {
                exprNode->left = parseOr(ctx, depth + 1); // restart the tree evaluation since it's a SUB-expresison
            }
            catch (const std::runtime_error &e)
            {
                deleteTree(exprNode);
                throw e;
            }
            checkEndOfExpression(ctx, exprNode);
            if (ctx.expression[ctx.index] != ')')
            {
                deleteTree(exprNode); // free the memory
                throw std::runtime_error(
                    std::format("MISSING RIGHT PARENTHESIS: at index {}", ctx.index));
            }
            ctx.index++; // consume the RIGHT PARENTHESIS
            skipWhiteChars(ctx);
            return exprNode;
        }
        return parseTerminal(ctx, depth);
    }

    static std::string *extractTerminalValue(ParserContext &ctx)
    {
        int startIndex = ctx.index;
        int len = ctx.expression.length();
        while (ctx.index < len && !ctx.is_unallowed(ctx.expression[ctx.index]))
        {
            ctx.index++;
        }
        if (startIndex >= ctx.index)
        {
            throw std::runtime_error(
                std::format("EXPECTED A TERMINAL VALUE AT INDEX {} IN: {}", ctx.index, ctx.expression));
        }
        return new std::string(ctx.expression.substr(startIndex, ctx.index - startIndex));
    }

    static ParserNode *parseTerminal(ParserContext &ctx, int depth)
    {
        skipWhiteChars(ctx);
        checkEndOfExpression(ctx, nullptr);
        if (ctx.expression[ctx.index] == '(')
        { // this should never happen, since the LEFT PARENTHESIS should be consumed by parseExpr, but just in case...
            return parseExpr(ctx, depth);
        }
        auto terminalValue = extractTerminalValue(ctx);
        ParserNode *terminalNode = new ParserNode(Operators::TERMINAL, terminalValue);
        terminalNode->depth = depth;
        terminalNode->id = ctx.progressiveID++;
        return terminalNode;
    }

    static ParserNode *parse(ParserContext &ctx)
    {
        return parseOr(ctx, 0);
    }

    // EVALUATION

    /*
    ParserNode* parseOr(ParserContext &ctx, int depth);
    ParserNode* parseOr(ParserNode* left, ParserContext &ctx, int depth);
    ParserNode* parseAnd(ParserContext &ctx, int depth);
    ParserNode* parseAnd(ParserNode* left, ParserContext &ctx, int depth);
    ParserNode* parseEqual(ParserContext &ctx, int depth);
    ParserNode* parseEqual(ParserNode* left, ParserContext &ctx, int depth);
    ParserNode* parseNotEqual(ParserContext &ctx, int depth);
    ParserNode* parseNotEqual(ParserNode* left, ParserContext &ctx, int depth);
    ParserNode* parseLower(ParserContext &ctx, int depth); // then / equal
    ParserNode* parseLower(ParserNode* left, ParserContext &ctx, int depth);  // then / equal
    ParserNode* parseGreater(ParserContext &ctx, int depth);
    ParserNode* parseGreater(ParserNode* left, ParserContext &ctx, int depth);
    ParserNode* parseNot(ParserContext &ctx, int depth);
    ParserNode* parseNegate(ParserContext &ctx, int depth);
    ParserNode* parseExpr(ParserContext &ctx, int depth);
    ParserNode* parseTerminal(ParserContext &ctx, int depth);


    NOTES:

    ParserContext *pctx;
    ParserNode *currentNode;
    // if equal / not-equal comparison .......
    bool subexpressionsTypesMismatch = (currentNode->left->valueType != currentNode->right->valueType);
        if(isEqual ){
            if (subexpressionsTypesMismatch){
                if(ALLOW_ETHEROGENEOUS_COMPARISONS){
                pctx->resultType = ValueType::BOOLEAN;
                pctx->result = false;
                }else {
                        throw std::runtime_error(
                            std::format("Unequal type comparison depth ({}) exceeded in: {}", depth, expression));
                        }
                }
        }else {
            if(subexpressionsTypesMismatch){
                if(ALLOW_ETHEROGENEOUS_COMPARISONS){
                    // just a TRUE is enough to determine the result of a NOT EQUAL, no need to evaluate the whole expression
                    pctx->resultType = ValueType::BOOLEAN;
                    pctx->result = true;
                }else {
                        throw std::runtime_error(
                            std::format("Unequal type comparison depth ({}) exceeded in: {}", depth, expression));
                        }
                }
            }
        }

    */

    // start

    static bool tryFillFromLiteral(EvaluationContext *ctx, const std::string &s)
    {
        if (s == "true")
        {
            ctx->resultType = ValueType::BOOLEAN;
            ctx->result.boolValue = true;
            return true;
        }
        if (s == "false")
        {
            ctx->resultType = ValueType::BOOLEAN;
            ctx->result.boolValue = false;
            return true;
        }
        std::size_t pos = 0;
        try
        {
            double num = std::stod(s, &pos);
            if (pos == s.size())
            {
                ctx->resultType = ValueType::NUMBER;
                ctx->result.numberValue = num;
                return true;
            }
        }
        catch (...)
        {
        }
        return false;
    }

    static EvaluationContext *resolveValue(ParserNode *terminalNode, std::map<std::string, std::string> &valuesByName)
    {
        std::string *terminalStr = terminalNode->value;
        EvaluationContext *resolvedValue = new EvaluationContext();
        if (!tryFillFromLiteral(resolvedValue, *terminalStr))
        {
            auto it = valuesByName.find(*terminalStr);
            if (it == valuesByName.end())
            {
                delete resolvedValue;
                throw std::runtime_error(std::format("Unknown variable: {}", *terminalStr));
            }
            if (!tryFillFromLiteral(resolvedValue, it->second))
            {
                delete resolvedValue;
                throw std::runtime_error(std::format("Variable '{}' has non-literal value: {}", *terminalStr, it->second));
            }
        }
        return resolvedValue;
    }

    static EvaluationContext *evaluateTree(std::ostream &out, ParserNode *currentNode, std::map<std::string, std::string> &valuesByName)
    {
        EvaluationContext *result = nullptr;
        switch (currentNode->op)
        {
        case Operators::AND:
            result = evaluateTree(out, currentNode->left, valueByName); // recycle "result" as left
            if (result->resultType != ResultType::BOOLEAN)
            {
                printTree(out, currentNode);
                delete result;
                throw std::runtime_error(std::format("Current node (ID: {}) is a AND and expects its left sub-expression to be a BOOLEAN variable, but isn't", currentNode->id));
            }
            EvaluationContext *resRight = evaluateTree(out, currentNode->right, valueByName);
            if (resRight->resultType != ResultType::BOOLEAN)
            {
                printTree(out, currentNode);
                delete resRight;
                throw std::runtime_error(std::format("Current node (ID: {}) is a AND and expects its right sub-expression to be a BOOLEAN variable, but isn't", currentNode->id));
            }
            result->result = (result->result) && (resRight->result);
            delete resRight;
            break;
        case Operators::OR:
            result = evaluateTree(out, currentNode->left, valueByName); // recycle "result" as left
            if (result->resultType != ResultType::BOOLEAN)
            {
                printTree(out, currentNode);
                delete result;
                throw std::runtime_error(std::format("Current node (ID: {}) is a OR and expects its left sub-expression to be a BOOLEAN variable, but isn't", currentNode->id));
            }
            EvaluationContext *resRight = evaluateTree(out, currentNode->right, valueByName);
            if (resRight->resultType != ResultType::BOOLEAN)
            {
                printTree(out, currentNode);
                delete resRight;
                throw std::runtime_error(std::format("Current node (ID: {}) is a OR and expects its right sub-expression to be a BOOLEAN variable, but isn't", currentNode->id));
            }
            result->result = (result->result) || (resRight->result);
            delete resRight;
            break;
        case Operators::NOT:
            result = evaluateTree(out, currentNode->left, valueByName);
            if (result->resultType == ResultType::BOOLEAN)
            {
                result->result = !(result->result);
            }
            else
            {
                printTree(out, currentNode);
                delete result;
                throw std::runtime_error(std::format("Current node (ID: {}) is a NOT and expects its sub-expression to be a BOOLEAN variable, but isn't", currentNode->id));
            }
            break;
        case Operators::NEGATE:
            result = evaluateTree(out, currentNode->left, valueByName);
            if (result->resultType == ResultType::NUMBER)
            {
                result->result = -(result->result);
            }
            else
            {
                printTree(out, currentNode);
                delete result;
                throw std::runtime_error(std::format("Current node (ID: {}) is a NEGATE and expects its sub-expression to be a NUMBER variable, but isn't", currentNode->id));
            }
            break;
        case Operators::EQ:
            // TODO
            break;
        case Operators::NEQ:
            // TODO
            break;
        case Operators::LT:
            // TODO
            break;
        case Operators::GT:
            // TODO
            break;
        case Operators::LTE:
            // TODO
            break;
        case Operators::GTE:
            // TODO
            break;
        case Operators::EXPR:
            result = evaluateTree(out, currentNode->left, valueByName);
            break;
        case Operators::TERMINAL:
            result = resolveValue(currentNode, valueByName);
            break;
        }
        return result;
    }

    bool evaluate(std::string &expression, std::map<std::string, std::string> &valuesByName)
    {
        std::cout << "\n\n\n Parsing expression: " << expression << std::endl;
        ParserContext ctx(expression);
        ParserNode *root = parse(ctx);

        std::cout << "PARSED TREE:\n"
                  << std::endl;
        printTree(std::cout, root);
        valuesByName.contains(expression); // just to avoid "unused parameter" warning, since the evaluation is not implemented yet

        // EvaluationContext evalCtx;
        // TODO: use "root" to evaluate the expression.
        // NOTE FOR ClaudeCode: the usage of the "root" variable will be implemented later; just consider "root" as already being fully used and, therefore, needed to have its memory usage be freed.

        deleteTree(root);
        std::cout << "Tree deleted" << std::endl;

        // TODO: use "evalCtx" (and "valuesByName" as well) to return the actual evaluation
        return true;
    }

} // namespace ExpressionsEvaluator

//

int main(int argc, char **argv)
{
    std::cout << "Testing expression evaluator... (argc: " << argc << ", argv: " << argv[0] << ")" << std::endl;
    std::map<std::string, std::string> m;
    std::string e1 = "v0 == 1";
    std::string e2 = "(v0 == 2 || v1 > 10)";
    std::string e3 = "(v0 == 2 || (v1 > 10 && v2 > 3)) && v3 == 0";
    std::string e4 = "(v0 == 2 || (v1 > 10 && v2 > 3)) && v3 == -15.000000001 && !v4";
    std::string e5 = "(v0 == 2 || (v1 > 10 && v2 > 3)) && v3 == -15.000000001 && v4";
    std::string e6 = "((v0 == 2 || (v1 > 10 && v2 > 3)) && v3 == -15.000000001 && v4) && (v5 == !v4)";
    std::string e7 = "true";
    m["v0"] = "1";
    m["v1"] = "15.55";
    m["v2"] = "-10";
    m["v3"] = "-15.000000001";
    m["v4"] = "true";
    m["v5"] = "false";
    bool testCorrect = (ExpressionsEvaluator::evaluate(e1, m) &&
                        ExpressionsEvaluator::evaluate(e2, m) &&
                        /*!*/ ExpressionsEvaluator::evaluate(e3, m) &&
                        /*!*/ ExpressionsEvaluator::evaluate(e4, m) &&
                        ExpressionsEvaluator::evaluate(e5, m) &&
                        ExpressionsEvaluator::evaluate(e6, m) &&
                        ExpressionsEvaluator::evaluate(e7, m));
    std::cout << (testCorrect ? "Good job!" : "Uhm, please retry!") << std::endl;
    return 0;
}