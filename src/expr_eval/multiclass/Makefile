# ─────────────────────────────────────────────────────────────────────────────
# Makefile — expr_eval multiclass project
# Targets:  all   build the demo executable (default)
#           test  build and run the unit-test executable
#           clean remove all generated files
# ─────────────────────────────────────────────────────────────────────────────

# ── Compiler & flags ──────────────────────────────────────────────────────────
CXX      := g++
CXXFLAGS := -std=c++26 -Wall -Wextra
# -MMD -MP: write a .d dependency file alongside every .o so that Make
#           knows which .o files to rebuild when a header changes.
DEPFLAGS := -MMD -MP
INC      := -I include/

# ── Build artefacts directory ─────────────────────────────────────────────────
BUILD_DIR := build

# ── Library sources (linked into both the demo and the test executable) ───────
LIB_SRCS := \
    src/types/Value.cpp               \
    src/ast/AstNode.cpp               \
    src/ast/BinaryNode.cpp            \
    src/ast/UnaryNode.cpp             \
    src/ast/TerminalNode.cpp          \
    src/ast/ExprNode.cpp              \
    src/ast/logical/NotNode.cpp       \
    src/ast/arithmetic/NegateNode.cpp \
    src/parser/Parser.cpp             \
    src/ExpressionEvaluator.cpp

# ── Derive .o paths:  src/foo/bar.cpp  →  build/src/foo/bar.o ────────────────
LIB_OBJS := $(patsubst %.cpp, $(BUILD_DIR)/%.o, $(LIB_SRCS))
MAIN_OBJ := $(BUILD_DIR)/main.o
TEST_OBJ := $(BUILD_DIR)/test/test_expr_eval.o

# ── Platform detection ────────────────────────────────────────────────────────
# Executables have .exe on Windows (including MSYS2); no extension on Linux.
ifeq ($(OS),Windows_NT)
    EXE_EXT := .exe
else
    EXE_EXT :=
endif

# ── Output executables ────────────────────────────────────────────────────────
MAIN_EXE := $(BUILD_DIR)/expr_eval_multi$(EXE_EXT)
TEST_EXE := $(BUILD_DIR)/expr_eval_test$(EXE_EXT)

# ── Include auto-generated header dependency files (silently skip on 1st build)
-include $(LIB_OBJS:.o=.d) $(MAIN_OBJ:.o=.d) $(TEST_OBJ:.o=.d)

# ─────────────────────────────────────────────────────────────────────────────
# Targets
# ─────────────────────────────────────────────────────────────────────────────

.PHONY: all test clean

# Default: build the demo program.
all: $(MAIN_EXE)

# Build the test executable then run it; non-zero exit propagates to Make.
test: $(TEST_EXE)
	./$(TEST_EXE)

# ── Link rules ────────────────────────────────────────────────────────────────

$(MAIN_EXE): $(LIB_OBJS) $(MAIN_OBJ)
	$(CXX) $(CXXFLAGS) $^ -o $@

$(TEST_EXE): $(LIB_OBJS) $(TEST_OBJ)
	$(CXX) $(CXXFLAGS) $^ -o $@

# ── Compile rule ──────────────────────────────────────────────────────────────
# Pattern matches any .cpp under the project root and produces the mirrored
# .o (and .d) under build/. The @mkdir -p creates parent directories on demand.

$(BUILD_DIR)/%.o: %.cpp
	@mkdir -p $(dir $@)
	$(CXX) $(CXXFLAGS) $(DEPFLAGS) $(INC) -c $< -o $@

# ── Clean ─────────────────────────────────────────────────────────────────────
# Remove the entire build/ tree (executables, objects, dependency files).
clean:
	rm -rf $(BUILD_DIR)
