# ─────────────────────────────────────────────────────────────────────────────
# Makefile — expr_eval_py   (C ABI bridge → Python ctypes)
# Targets:  all    build the shared library + copy runtime deps (default)
#           test   run pytest unit tests
#           clean  remove generated files
#
# Supports: Windows 11 (MSYS2 UCRT64)  and  Linux (Mint / Ubuntu, GCC ≥ 15)
# ─────────────────────────────────────────────────────────────────────────────

# ── Compiler & base flags ─────────────────────────────────────────────────────
CXX      := g++
CXXFLAGS := -std=c++26 -O2 -Wall -Wextra
# Generate dependency files (.d) automatically
CPPFLAGS := -MMD -MP

# ── Platform detection ────────────────────────────────────────────────────────
PYTHON := $(shell command -v python3 2>/dev/null || command -v python 2>/dev/null)
ifeq ($(PYTHON),)
    $(error Python not found on PATH. Install Python and ensure 'python3' or 'python' is accessible.)
endif

ifeq ($(OS),Windows_NT)
    # Windows: produce a DLL; embed GCC runtime statically.
    LIB_SUFFIX     := .dll
    LDFLAGS        := -shared -static-libgcc -static-libstdc++
    
    # Use MSYSTEM_PREFIX (e.g., /ucrt64)
    PREFIX         := $(if $(MSYSTEM_PREFIX),$(MSYSTEM_PREFIX),/ucrt64)
    WINPTHREAD_SRC := $(PREFIX)/bin/libwinpthread-1.dll
    WINPTHREAD_DST := expr_eval_py/libwinpthread-1.dll
    
    RUNTIME_TARGET := $(WINPTHREAD_DST)
    CLEAN_RUNTIME  = rm -f "$(WINPTHREAD_DST)"
else
    # Linux: produce a .so; -fPIC is mandatory for shared libs.
    LIB_SUFFIX     := .so
    CXXFLAGS       += -fPIC
    LDFLAGS        := -shared -static-libgcc -static-libstdc++
    
    RUNTIME_TARGET :=
    CLEAN_RUNTIME  = :
endif

# ── Paths & Sources ───────────────────────────────────────────────────────────
EXPR_EVAL_ROOT := ../expr_eval/multiclass
INC            := -I $(EXPR_EVAL_ROOT)/include

# Separate the sources to map them cleanly into the build directory
LIB_SRCS_CORE := \
    $(EXPR_EVAL_ROOT)/src/types/Value.cpp               \
    $(EXPR_EVAL_ROOT)/src/ast/AstNode.cpp               \
    $(EXPR_EVAL_ROOT)/src/ast/BinaryNode.cpp            \
    $(EXPR_EVAL_ROOT)/src/ast/UnaryNode.cpp             \
    $(EXPR_EVAL_ROOT)/src/ast/TerminalNode.cpp          \
    $(EXPR_EVAL_ROOT)/src/ast/ExprNode.cpp              \
    $(EXPR_EVAL_ROOT)/src/ast/logical/NotNode.cpp       \
    $(EXPR_EVAL_ROOT)/src/ast/arithmetic/NegateNode.cpp \
    $(EXPR_EVAL_ROOT)/src/parser/Parser.cpp             \
    $(EXPR_EVAL_ROOT)/src/ExpressionEvaluator.cpp

LIB_SRCS_BRIDGE := bridge/bridge.cpp

# ── Object Files & Build Directory ────────────────────────────────────────────
OBJ_DIR := build

# Map core sources: ../expr_eval/multiclass/src/xyz.cpp -> build/src/xyz.o
OBJS_CORE := $(patsubst $(EXPR_EVAL_ROOT)/src/%.cpp, $(OBJ_DIR)/src/%.o, $(LIB_SRCS_CORE))

# Map bridge sources: bridge/xyz.cpp -> build/bridge/xyz.o
OBJS_BRIDGE := $(patsubst bridge/%.cpp, $(OBJ_DIR)/bridge/%.o, $(LIB_SRCS_BRIDGE))

# Combine them for the linker
OBJS := $(OBJS_CORE) $(OBJS_BRIDGE)
DEPS := $(OBJS:.o=.d)

# ── Output ────────────────────────────────────────────────────────────────────
LIB := expr_eval_py/_expr_eval_core$(LIB_SUFFIX)

# ─────────────────────────────────────────────────────────────────────────────

.PHONY: all test clean

all: $(LIB) $(RUNTIME_TARGET)

# Link all object files into the final shared library
$(LIB): $(OBJS)
	@mkdir -p $(dir $@)
	$(CXX) $(CXXFLAGS) $(LDFLAGS) $^ -o $@
	@echo "Built: $@"

# Compile core .cpp files to .o files inside build/src/
$(OBJ_DIR)/src/%.o: $(EXPR_EVAL_ROOT)/src/%.cpp
	@mkdir -p $(dir $@)
	$(CXX) $(CPPFLAGS) $(CXXFLAGS) $(INC) -c $< -o $@

# Compile bridge .cpp files to .o files inside build/bridge/
$(OBJ_DIR)/bridge/%.o: bridge/%.cpp
	@mkdir -p $(dir $@)
	$(CXX) $(CPPFLAGS) $(CXXFLAGS) $(INC) -c $< -o $@

# Copy runtime DLL (Windows only)
$(WINPTHREAD_DST): $(WINPTHREAD_SRC)
	@mkdir -p $(dir $@)
	@cp -f "$<" "$@"
	@echo "Copied runtime: $@"

test: all
	$(PYTHON) -m pytest tests/ -v

clean:
	rm -rf $(OBJ_DIR)
	rm -f $(LIB)
	@$(CLEAN_RUNTIME)
	@echo "Cleaned build artifacts."

# Include the generated dependency files so Make knows when headers change
-include $(DEPS)