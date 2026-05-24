cmake_minimum_required(VERSION 3.18)
project(fcpp_chain_decaying CXX)

set(CMAKE_CXX_STANDARD 14)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Include fcpp headers from git-ignored clone
include_directories(${CMAKE_SOURCE_DIR}/../fcpp_clone_GITIGNORE_ME/src)
include_directories(${CMAKE_SOURCE_DIR}/../fcpp_clone_GITIGNORE_ME/src/external)

# Build executable
add_executable(chain_decaying
    chain_decaying.cpp
)

# Link OpenGL (all platforms) + X11 (Linux only — macOS and Windows have no X11)
if(APPLE)
    # macOS: OpenGL via system framework; X11 not available by default
    find_package(OpenGL REQUIRED)
    target_link_libraries(chain_decaying OpenGL::GL)
elseif(WIN32)
    # Windows: OpenGL via CMake's FindOpenGL module
    find_package(OpenGL REQUIRED)
    target_link_libraries(chain_decaying OpenGL::GL)
else()
    # Linux / other POSIX: fcpp GUI requires both X11 and OpenGL
    find_package(X11 REQUIRED)
    find_package(OpenGL REQUIRED)
    target_link_libraries(chain_decaying X11::X11 OpenGL::GL)
endif()




# target declaration
#fcpp_target(./run/exercises.cpp ON)
#set(ALL_TARGETS
#    exercises
#    exercises_1_mountains_peaks
#    exercises_3
#    exercises_4
#)
#foreach(src_targets ${ALL_TARGETS})
#    fcpp_target(./run/${src_targets}.cpp ON)
#endforeach()
