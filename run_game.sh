#!/bin/bash
# Run the CLI-built game. Runs from a dir two levels under the project root so
# the game's "../../res/" resource path resolves correctly.
cd "$(dirname "$0")"
if [ ! -x build_local/ProjectRetro ]; then echo "Build first: ./build_local.sh"; exit 1; fi
mkdir -p build_local/run
cd build_local/run
exec ../ProjectRetro
