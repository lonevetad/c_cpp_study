// Self-contained unit tests for ExprEval — no external test framework required.
// Build & run:  make test   (from multiclass/)

#include "expr_eval/ExpressionEvaluator.hpp"
#include "expr_eval/errors.hpp"

#include <iostream>
#include <sstream>
#include <string>

// ── minimal test harness ──────────────────────────────────────────────────────

static int gPassed = 0;
static int gFailed = 0;

// Emits PASS/FAIL and updates counters.
static void check(bool cond, const char* label) {
    if (cond) {
        ++gPassed;
        std::cout << "  PASS  " << label << "\n";
    } else {
        ++gFailed;
        std::cout << "  FAIL  " << label << "\n";
    }
}

#define EXPECT_TRUE(expr, label)  check((expr), label)
#define EXPECT_FALSE(expr, label) check(!(expr), label)

// Passes only if `expr` throws an exception of exactly `ExcType`.
#define EXPECT_THROW(ExcType, expr, label)                          \
    do {                                                             \
        bool caught_ = false;                                        \
        try { (void)(expr); }                                        \
        catch (const ExcType&) { caught_ = true; }                  \
        catch (...) {}                                               \
        check(caught_, label);                                       \
    } while (false)

// ── helpers ───────────────────────────────────────────────────────────────────

// Calls ExprEval::evaluate but suppresses its parse-tree cout output so that
// test PASS/FAIL lines remain readable.
static bool eval(std::string_view expr, const ExprEval::Variables& vars) {
    std::ostringstream sink;
    std::streambuf* prev = std::cout.rdbuf(sink.rdbuf());
    try {
        bool r = ExprEval::evaluate(expr, vars);
        std::cout.rdbuf(prev);
        return r;
    } catch (...) {
        std::cout.rdbuf(prev);
        throw;
    }
}

// Canonical variable set mirroring main.cpp.
static ExprEval::Variables makeVars() {
    ExprEval::Variables m;
    m["v0"] = "1";
    m["v1"] = "15.55";
    m["v2"] = "5";
    m["v3"] = "-15.000000001";
    m["v4"] = "true";
    m["v5"] = "false";
    return m;
}

// ── test sections ─────────────────────────────────────────────────────────────

static void testLiterals() {
    std::cout << "\n[Literals]\n";
    ExprEval::Variables empty;
    EXPECT_TRUE(eval("true",  empty), "literal true");
    EXPECT_FALSE(eval("false", empty), "literal false");
}

static void testTerminalVariable() {
    std::cout << "\n[Terminal variable lookup]\n";
    ExprEval::Variables m;
    m["yes"] = "true";
    m["no"]  = "false";
    EXPECT_TRUE(eval("yes", m), "variable 'yes' resolves to true");
    EXPECT_FALSE(eval("no",  m), "variable 'no'  resolves to false");
}

static void testEquality() {
    std::cout << "\n[Equality == / !=]\n";
    auto m = makeVars();
    EXPECT_TRUE(eval("v0 == 1",     m), "v0 == 1");
    EXPECT_FALSE(eval("v0 == 2",    m), "v0 == 2  (false)");
    EXPECT_TRUE(eval("v0 != 2",     m), "v0 != 2");
    EXPECT_FALSE(eval("v0 != 1",    m), "v0 != 1  (false)");
    EXPECT_TRUE(eval("v4 == true",  m), "bool eq:  v4 == true");
    EXPECT_FALSE(eval("v4 == false",m), "bool eq:  v4 == false (false)");
    EXPECT_TRUE(eval("v5 == false", m), "bool eq:  v5 == false");
    // heterogeneous (bool vs number): kAllowHeterogeneousComparisons=true
    //   EQ returns false, NEQ returns true
    EXPECT_FALSE(eval("v4 == 1",    m), "hetero EQ  → false");
    EXPECT_TRUE(eval("v4 != 1",     m), "hetero NEQ → true");
}

static void testNumericComparisons() {
    std::cout << "\n[Numeric comparisons < <= > >=]\n";
    auto m = makeVars();
    EXPECT_TRUE(eval("v1 > 10",     m), "v1 > 10");
    EXPECT_FALSE(eval("v1 > 20",    m), "v1 > 20  (false)");
    EXPECT_TRUE(eval("v1 >= 15.55", m), "v1 >= 15.55");
    EXPECT_FALSE(eval("v1 >= 16",   m), "v1 >= 16  (false)");
    EXPECT_TRUE(eval("v2 < 10",     m), "v2 < 10");
    EXPECT_FALSE(eval("v2 < 3",     m), "v2 < 3   (false)");
    EXPECT_TRUE(eval("v2 <= 5",     m), "v2 <= 5");
    EXPECT_FALSE(eval("v2 <= 4",    m), "v2 <= 4  (false)");
    EXPECT_TRUE(eval("v3 < 0",      m), "v3 < 0   (negative number)");
    EXPECT_TRUE(eval("v3 <= 0",     m), "v3 <= 0");
    EXPECT_FALSE(eval("v3 > 0",     m), "v3 > 0   (false)");
}

static void testLogicalAnd() {
    std::cout << "\n[Logical AND &&]\n";
    auto m = makeVars();
    EXPECT_TRUE(eval("v4 && v4",  m), "true  && true");
    EXPECT_FALSE(eval("v4 && v5", m), "true  && false");
    EXPECT_FALSE(eval("v5 && v4", m), "false && true  (short-circuit)");
    EXPECT_FALSE(eval("v5 && v5", m), "false && false");
    // Short-circuit: RHS 'unknown' is never evaluated, so no EvaluationError.
    ExprEval::Variables half;
    half["ok"] = "false";
    EXPECT_FALSE(eval("ok && unknown", half), "false && <unknown> short-circuits, no throw");
}

static void testLogicalOr() {
    std::cout << "\n[Logical OR ||]\n";
    auto m = makeVars();
    EXPECT_TRUE(eval("v4 || v4",  m), "true  || true");
    EXPECT_TRUE(eval("v4 || v5",  m), "true  || false");
    EXPECT_TRUE(eval("v5 || v4",  m), "false || true");
    EXPECT_FALSE(eval("v5 || v5", m), "false || false");
    // Short-circuit: RHS 'unknown' is never evaluated, so no EvaluationError.
    ExprEval::Variables half;
    half["ok"] = "true";
    EXPECT_TRUE(eval("ok || unknown", half), "true || <unknown> short-circuits, no throw");
}

static void testNot() {
    std::cout << "\n[NOT ! / double-NOT elimination]\n";
    auto m = makeVars();
    EXPECT_FALSE(eval("!v4",   m), "!true  → false");
    EXPECT_TRUE(eval("!v5",    m), "!false → true");
    EXPECT_TRUE(eval("!!v4",   m), "!!true  (double-NOT optimized out)");
    EXPECT_FALSE(eval("!!v5",  m), "!!false (double-NOT optimized out)");
    EXPECT_FALSE(eval("!!!v4", m), "!!!true");
    EXPECT_TRUE(eval("!!!v5",  m), "!!!false");
}

static void testNegate() {
    std::cout << "\n[NEGATE - / double-NEGATE elimination]\n";
    auto m = makeVars();
    // --x collapses to x during optimization, then 5.0 == 5.0 → true.
    EXPECT_TRUE(eval("--v2 == v2",  m), "--v2 == v2  (double-negate collapsed)");
    // -(-15.000000001) = 15.000000001 > 0 → true.
    EXPECT_TRUE(eval("-v3 > 0",     m), "-v3 > 0    (negate negative)");
    // -(5) = -5, which is < 0.
    EXPECT_FALSE(eval("-v2 > 0",    m), "-v2 > 0    (negate positive → false)");
    EXPECT_TRUE(eval("-v2 < 0",     m), "-v2 < 0");
    EXPECT_TRUE(eval("-v2 == -5",   m), "-v2 == -5");
}

static void testParentheses() {
    std::cout << "\n[Parentheses / ExprNode collapse]\n";
    auto m = makeVars();
    EXPECT_TRUE(eval("(v4)",           m), "(true)");
    EXPECT_TRUE(eval("((v4))",         m), "((true))");
    EXPECT_TRUE(eval("(v0 == 1)",      m), "(v0 == 1)");
    EXPECT_FALSE(eval("(v0 == 2)",     m), "(v0 == 2)  false");
    EXPECT_TRUE(eval("(v4 || v5)",     m), "(true || false)");
    EXPECT_FALSE(eval("(v4 && v5)",    m), "(true && false)");
}

static void testComplex() {
    std::cout << "\n[Complex expressions — from main.cpp]\n";
    auto m = makeVars();
    EXPECT_TRUE(eval("v0 == 1", m),
        "e1: v0==1");
    EXPECT_TRUE(eval("(v0 == 2 || v1 > 10)", m),
        "e2: v0==2||v1>10");
    EXPECT_FALSE(eval("(v0 == 2 || (v1 > 10 && v2 > 3)) && v3 == 0", m),
        "e3: ... && v3==0   (false)");
    EXPECT_FALSE(eval("(v0 == 2 || (v1 > 10 && v2 > 3)) && v3 == -15.000000001 && !v4", m),
        "e4: ... && !v4     (false)");
    EXPECT_TRUE(eval("(v0 == 2 || (v1 > 10 && v2 > 3)) && v3 == -15.000000001 && v4", m),
        "e5: ... && v4");
    EXPECT_TRUE(eval("((v0 == 2 || (v1 > 10 && v2 > 3)) && v3 == -15.000000001 && v4) && (v5 == !v4)", m),
        "e6: e5 && (v5==!v4)");
    EXPECT_TRUE(eval("true", {}),
        "e7: bare literal true");
}

static void testParseErrors() {
    std::cout << "\n[ParseError — malformed input]\n";
    ExprEval::Variables empty;
    EXPECT_THROW(ExprEval::ParseError, eval("", empty),          "empty expression");
    EXPECT_THROW(ExprEval::ParseError, eval("(v0 == 1", empty),  "unclosed parenthesis");
    EXPECT_THROW(ExprEval::ParseError, eval("v0 == ", empty),    "trailing == (no RHS)");
    EXPECT_THROW(ExprEval::ParseError, eval("v0 &&", empty),     "trailing && (no RHS)");
    EXPECT_THROW(ExprEval::ParseError, eval("v0 ||", empty),     "trailing || (no RHS)");
    EXPECT_THROW(ExprEval::ParseError, eval("!", empty),         "lone ! (no operand)");
    EXPECT_THROW(ExprEval::ParseError, eval("-", empty),         "lone - (no operand)");
}

static void testEvaluationErrors() {
    std::cout << "\n[EvaluationError — type and lookup failures]\n";
    ExprEval::Variables empty;
    ExprEval::Variables m;
    m["num"] = "42";

    // Root evaluates to NUMBER, not BOOLEAN → ExpressionEvaluator throws.
    EXPECT_THROW(ExprEval::EvaluationError, eval("5",             empty), "bare number at root");
    EXPECT_THROW(ExprEval::EvaluationError, eval("1.5",           empty), "bare float at root");

    // Variable not in the map.
    EXPECT_THROW(ExprEval::EvaluationError, eval("unknown",       empty), "unknown variable");

    // Variable present but its string value is not a bool or number.
    ExprEval::Variables bad;
    bad["x"] = "not_a_value";
    EXPECT_THROW(ExprEval::EvaluationError, eval("x",             bad),   "non-literal variable value");

    // Order comparison requires both operands to be NUMBER.
    EXPECT_THROW(ExprEval::EvaluationError, eval("true > false",  empty), "bool > bool");
    EXPECT_THROW(ExprEval::EvaluationError, eval("true < false",  empty), "bool < bool");

    // NEGATE requires a NUMBER operand.
    EXPECT_THROW(ExprEval::EvaluationError, eval("-true",         empty), "negate boolean");

    // Logical AND/OR require both operands to be BOOLEAN.
    EXPECT_THROW(ExprEval::EvaluationError, eval("num && true",   m),     "number && bool");
    EXPECT_THROW(ExprEval::EvaluationError, eval("true && num",   m),     "bool && number");
    EXPECT_THROW(ExprEval::EvaluationError, eval("num || false",  m),     "number || bool");
}

// ── entry point ───────────────────────────────────────────────────────────────

int main() {
    std::cout << "=== expr_eval unit tests ===\n";

    testLiterals();
    testTerminalVariable();
    testEquality();
    testNumericComparisons();
    testLogicalAnd();
    testLogicalOr();
    testNot();
    testNegate();
    testParentheses();
    testComplex();
    testParseErrors();
    testEvaluationErrors();

    std::cout << "\n============================\n";
    std::cout << "  passed: " << gPassed << "\n";
    std::cout << "  failed: " << gFailed << "\n";
    std::cout << (gFailed == 0 ? "ALL TESTS PASSED\n" : "SOME TESTS FAILED\n");
    return gFailed == 0 ? 0 : 1;
}
