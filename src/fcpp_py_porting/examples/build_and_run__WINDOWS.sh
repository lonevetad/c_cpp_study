#/bin/bash

# Create build directory
echo "making the build folder"
mkdir -p build
cd build

# Configure with CMake (C++14, as per fcpp requirement)
cmake -G "Unix Makefiles" \
    -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_CXX_STANDARD=14 \
    ..

# Build
mingw32-make -j4

# Output: 
./chain_decaying.exe