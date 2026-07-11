// Force-included on non-MSVC builds. Modern libc++/libstdc++ no longer pull
// these in transitively the way 2019-era toolchains did, so the original
// sources (which use assert(), fixed-width ints, size_t, memcpy, etc. without
// always including the header) fail to compile. Including them here keeps the
// project buildable on current compilers without touching every source file.
#pragma once
#include <cassert>
#include <cstdint>
#include <cstddef>
#include <cstring>
#include <cstdio>
