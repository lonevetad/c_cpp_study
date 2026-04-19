// C ABI bridge between the ExprEval C++26 library and Python ctypes.
//
// ALL C++ exceptions are caught here.  Only plain C types cross the boundary.
// This makes the DLL loadable from any Python build regardless of compiler.

#include "expr_eval/ExpressionEvaluator.hpp"
#include "expr_eval/errors.hpp"

#include <cstdint>
#include <cstring>
#include <iostream>
#include <sstream>

// ── cross-platform export macro ───────────────────────────────────────────────
#ifdef _WIN32
#  define EXPR_EXPORT __declspec(dllexport)
#else
#  define EXPR_EXPORT __attribute__((visibility("default")))
#endif

// ── error codes returned to Python ───────────────────────────────────────────
static constexpr int32_t EXPR_OK              = 0;
static constexpr int32_t EXPR_ERR_PARSE       = 1;
static constexpr int32_t EXPR_ERR_EVALUATION  = 2;
static constexpr int32_t EXPR_ERR_INTERNAL    = 3;

// ── helpers ───────────────────────────────────────────────────────────────────

// Safe, truncating string copy — avoids deprecated strncpy.
static void safe_copy(char* dst, int32_t dst_size, const char* src) noexcept {
    if (!dst || dst_size <= 0) return;
    std::size_t len = std::strlen(src);
    std::size_t copy_len = (len < static_cast<std::size_t>(dst_size - 1))
                           ? len : static_cast<std::size_t>(dst_size - 1);
    std::memcpy(dst, src, copy_len);
    dst[copy_len] = '\0';
}

// RAII cout suppressor — redirects stdout to a sink for the lifetime of this object.
struct CoutSuppressor {
    std::ostringstream  sink;
    std::streambuf*     prev;
    CoutSuppressor()  : prev(std::cout.rdbuf(sink.rdbuf())) {}
    ~CoutSuppressor()   { std::cout.rdbuf(prev); }
};

// ── public C API ──────────────────────────────────────────────────────────────

extern "C" {

// Evaluate a boolean expression.
//
// Parameters
// ----------
// expression      Null-terminated expression string.
// var_keys        Array of `var_count` null-terminated variable name strings.
// var_values      Array of `var_count` null-terminated variable value strings.
// var_count       Number of variables (may be 0).
// verbose         1 = print parsed AST to stdout; 0 = suppress all C++ output.
// result_out      Set to 1 (true) or 0 (false) on success.
// error_buf       Buffer filled with the error message on failure.
// error_buf_size  Size of error_buf in bytes.
//
// Returns
// -------
// EXPR_OK (0)             on success   → read *result_out.
// EXPR_ERR_PARSE (1)      on ParseError.
// EXPR_ERR_EVALUATION (2) on EvaluationError.
// EXPR_ERR_INTERNAL (3)   on unexpected exception.
EXPR_EXPORT int32_t expr_eval_evaluate(
    const char*  expression,
    const char** var_keys,
    const char** var_values,
    int32_t      var_count,
    int32_t      verbose,
    int32_t*     result_out,
    char*        error_buf,
    int32_t      error_buf_size)
{
    try {
        ExprEval::Variables vars;
        for (int32_t i = 0; i < var_count; ++i)
            vars[var_keys[i]] = var_values[i];

        bool result;
        if (verbose) {
            result = ExprEval::evaluate(expression, vars);
        } else {
            CoutSuppressor suppress;
            result = ExprEval::evaluate(expression, vars);
        }

        *result_out = result ? 1 : 0;
        return EXPR_OK;

    } catch (const ExprEval::ParseError& e) {
        safe_copy(error_buf, error_buf_size, e.what());
        return EXPR_ERR_PARSE;
    } catch (const ExprEval::EvaluationError& e) {
        safe_copy(error_buf, error_buf_size, e.what());
        return EXPR_ERR_EVALUATION;
    } catch (const std::exception& e) {
        safe_copy(error_buf, error_buf_size, e.what());
        return EXPR_ERR_INTERNAL;
    } catch (...) {
        safe_copy(error_buf, error_buf_size, "Unknown internal error");
        return EXPR_ERR_INTERNAL;
    }
}

// Returns the library version string — also used by Python to verify the DLL loaded.
EXPR_EXPORT const char* expr_eval_version(void) {
    return "1.0.0";
}

} // extern "C"
