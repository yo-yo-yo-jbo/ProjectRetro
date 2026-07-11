#!/bin/bash
# Build ProjectRetro from the command line (Homebrew SDL2). Alternative to the
# Xcode flow in README.md. Requires: brew install sdl2 sdl2_image sdl2_mixer sdl2_ttf
set -e
cd "$(dirname "$0")"
mkdir -p build_local && cd build_local
cmake -G "Unix Makefiles" -DCMAKE_PREFIX_PATH=/opt/homebrew -DCMAKE_BUILD_TYPE=Debug ../source
make -j4
echo "Built: $(pwd)/ProjectRetro   (run with ../run_game.sh)"
