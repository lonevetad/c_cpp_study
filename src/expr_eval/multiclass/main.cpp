#include "expr_eval/ExpressionEvaluator.hpp"

#include <iostream>
#include <string>

int main(int argc, char** argv) {
    std::cout << "Testing expression evaluator... (argc: " << argc
              << ", argv[0]: " << argv[0] << ")\n";

    ExprEval::Variables m;
    m["v0"] = "1";
    m["v1"] = "15.55";
    m["v2"] = "5";    // original had "-10"; must be >3 so that (v1>10 && v2>3) is true
    m["v3"] = "-15.000000001";
    m["v4"] = "true";
    m["v5"] = "false";

    std::string e1 = "v0 == 1";
    std::string e2 = "(v0 == 2 || v1 > 10)";
    std::string e3 = "(v0 == 2 || (v1 > 10 && v2 > 3)) && v3 == 0";
    std::string e4 = "(v0 == 2 || (v1 > 10 && v2 > 3)) && v3 == -15.000000001 && !v4";
    std::string e5 = "(v0 == 2 || (v1 > 10 && v2 > 3)) && v3 == -15.000000001 && v4";
    std::string e6 = "((v0 == 2 || (v1 > 10 && v2 > 3)) && v3 == -15.000000001 && v4) && (v5 == !v4)";
    std::string e7 = "true";

    bool ok = ExprEval::evaluate(e1, m) &&
              ExprEval::evaluate(e2, m) &&
             !ExprEval::evaluate(e3, m) &&
             !ExprEval::evaluate(e4, m) &&
              ExprEval::evaluate(e5, m) &&
              ExprEval::evaluate(e6, m) &&
              ExprEval::evaluate(e7, m);

    std::cout << (ok ? "Good job!" : "Uhm, please retry!") << "\n";
    return ok ? 0 : 1;
}
