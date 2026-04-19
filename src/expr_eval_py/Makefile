# ─────────────────────────────────────────────────────────────────────────────
# Makefile — expr_eval_py   (C ABI bridge → Python ctypes)
# Targets:  all    build the shared library + copy runtime deps (default)
#           test   run pytest unit tests
#           clean  remove generated files
# ─────────────────────────────────────────────────────────────────────────────

# ── Compiler & flags ──────────────────────────────────────────────────────────
CXX      := g++
CXXFLAGS := -std=c++26 -O2 -Wall -Wextra

# -shared           : produce a shared library (.dll on Windows)
# -static-libgcc    : embed libgcc — no external libgcc_s*.dll needed
# -static-libstdc++ : embed libstdc++ — no external libstdc++-6.dll needed
# libwinpthread-1.dll cannot be fully eliminated because libstdc++ references
# it internally; we copy it alongside the DLL instead (see 'all' target).
LDFLAGS  := -shared -static-libgcc -static-libstdc++

# ── Path to the C++ library (sibling directory) ───────────────────────────────
EXPR_EVAL_ROOT := ../expr_eval/multiclass

INC := -I $(EXPR_EVAL_ROOT)/include

# ── C++ library source files (same set as multiclass/Makefile) ───────────────
LIB_SRCS := \
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

# ── Output: DLL lands inside the Python package directory ────────────────────
# __init__.py loads it via: pathlib.Path(__file__).parent / "_expr_eval_core.dll"
DLL := expr_eval_py/_expr_eval_core.dll

# ── MSYS2 runtime dependency that libstdc++ drags in ─────────────────────────
# Copied into the package dir so Windows finds it when loading the main DLL.
WINPTHREAD_SRC := /c/msys64/ucrt64/bin/libwinpthread-1.dll
WINPTHREAD_DST := expr_eval_py/libwinpthread-1.dll

# ── Python interpreter ────────────────────────────────────────────────────────
PYTHON := /c/python314/python.exe

# ─────────────────────────────────────────────────────────────────────────────

.PHONY: all test clean

# Build the DLL and copy the winpthread runtime next to it.
# __init__.py calls os.add_dll_directory(package_dir) before ctypes.CDLL so
# Windows finds libwinpthread-1.dll automatically.
all: $(DLL)
	cp -f "$(WINPTHREAD_SRC)" "$(WINPTHREAD_DST)"
	@echo "Copied runtime: $(WINPTHREAD_DST)"

$(DLL): bridge/bridge.cpp $(LIB_SRCS)
	$(CXX) $(CXXFLAGS) $(LDFLAGS) $(INC) $^ -o $@
	@echo "Built: $@"

# Run pytest from this directory so expr_eval_py/ is found as a package.
test: all
	$(PYTHON) -m pytest tests/ -v

# Remove DLL and copied runtime.
clean:
	rm -f $(DLL) $(WINPTHREAD_DST)
