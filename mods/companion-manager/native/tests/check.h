#pragma once
#include <cstdio>
#include <cstdlib>

// Release builds define NDEBUG, which turns assert() into a no-op and left every rule target
// reporting success without running a single check. These tests must fail loudly in every
// configuration, so they use an unconditional check instead.
#define CHECK(condition)                                                                                 \
    ((condition) ? static_cast<void>(0)                                                                  \
                 : (std::fprintf(stderr, "CHECK failed: %s (%s:%d)\n", #condition, __FILE__, __LINE__), \
                    std::abort()))
