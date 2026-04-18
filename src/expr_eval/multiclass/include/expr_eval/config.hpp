#pragma once

#include <array>

namespace ExprEval {

inline constexpr int kMaxRecursionDepth = 10000;

inline constexpr bool kAllowHeterogeneousComparisons = true;

inline constexpr std::array<bool, 256> kUnallowedCharsTerminal = []() {
    std::array<bool, 256> result{};
    constexpr std::array chars{
        ' ', '\t', '\n', '(', ')', '!', '&', '|', '=', '<', '>', ',',
        '+', '-', '*', '/', '\'', '\"', '\\', '#', '@', '[', ']', '{',
        '}', ';', ':', '?', '^', '%', '~', '`'
    };
    for (char c : chars)
        result[static_cast<unsigned char>(c)] = true;
    return result;
}();

} // namespace ExprEval
