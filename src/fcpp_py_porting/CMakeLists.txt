cmake_minimum_required(VERSION 3.20)
project(fcpp_py_porting CXX)

# Enforce C++26
set(CMAKE_CXX_STANDARD 26)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

include(FetchContent)

# Fetch the FCPP project
FetchContent_Declare(
    fcpp
    GIT_REPOSITORY https://github.com/fcpp/fcpp.git
    GIT_TAG        588904054606802c1a92a7e6f8966250723fbad3 # A specific commit hash is preferred over "master" for stability
)
FetchContent_MakeAvailable(fcpp)

# Fetch nanobind and its required dependency
FetchContent_Declare(
    nanobind
    GIT_REPOSITORY https://github.com/wjakob/nanobind.git
    GIT_TAG        v2.4.0 # It's safer to use a specific version tag
    GIT_SUBMODULES_RECURSE ON
)
# 'fcpp_ext' is the name of the resulting Python module: """ import fcpp_ext """
nanobind_add_module(fcpp_ext 
    src/main.cpp # The bridge file
)

# ...
# ... Later, link it to the bridge target:
# target_link_libraries(fcpp_ext PRIVATE fcpp) # is "fcpp_ext" the right choice here for the Python module? It seems so
