set_xmakever("2.8.2")
includes("../../../reference/example-skse-plugin/lib/commonlibsse-ng")
set_project("ConditionActorGuard")
set_version("0.1.0")
set_languages("c++23")
add_rules("mode.release", "mode.debug")

target("ConditionActorGuard")
    add_deps("commonlibsse-ng")
    add_cxxflags("/utf-8")
    add_rules("commonlibsse-ng.plugin", {
        name = "ConditionActorGuard",
        author = "linos",
        description = "Stop Skyrim SE 1.5.97 actor-only condition functions from dereferencing a null actor"
    })
    add_files("src/main.cpp")
    add_headerfiles("src/guard_code.h")

target("GuardCodeTests")
    set_kind("binary")
    set_default(false)
    add_cxxflags("/utf-8")
    add_includedirs("src")
    add_files("tests/guard.cpp")
