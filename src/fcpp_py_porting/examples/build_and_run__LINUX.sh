#/bin/bash

# Create build directory
echo "making the build folder"
mkdir -p build
cd build



# Configure (requires X11 and OpenGL development packages)
cmake -G "Unix Makefiles" \
    -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_CXX_STANDARD=14 \
    ..

# Build
make -j4

# Output:
./chain_decaying