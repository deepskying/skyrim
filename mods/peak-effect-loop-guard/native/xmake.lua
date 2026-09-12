set_xmakever("2.8.2")
includes("../../../reference/example-skse-plugin/lib/commonlibsse-ng")
set_project("PeakEffectLoopGuard")
set_version("0.1.0")
set_languages("c++23")
add_rules("mode.release", "mode.debug")

target("PeakEffectLoopGuard")
    add_deps("commonlibsse-ng")
    add_cxxflags("/utf-8")
    add_rules("commonlibsse-ng.plugin", {
        name = "PeakEffectLoopGuard",
        author = "linos",
        description = "Guard the Skyrim SE 1.5.97 peak effect self-loop traversal"
    })
    add_files("src/main.cpp")
    add_headerfiles("src/guard_code.h")

target("GuardCodeTests")
    set_kind("binary")
    set_default(false)
    add_cxxflags("/utf-8")
    add_includedirs("src")
    add_files("tests/guard.cpp")
