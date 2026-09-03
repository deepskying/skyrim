set_xmakever("2.8.2")

includes("../../../reference/example-skse-plugin/lib/commonlibsse-ng")

set_project("FollowerSpellbookManager")
set_version("0.9.1")
set_languages("c++23")
set_warnings("allextra")
set_policy("package.requires_lock", true)

add_requires("nlohmann_json")

add_rules("mode.release", "mode.debug")
add_rules("plugin.vsxmake.autoupdate")

target("FollowerSpellbookManager")
    add_deps("commonlibsse-ng")
    add_packages("nlohmann_json")
    add_rules("commonlibsse-ng.plugin", {
        name = "FollowerSpellbookManager",
        author = "linos",
        description = "Teach spell tomes to followers through a Prisma UI panel"
    })
    add_files("src/**.cpp")
    add_headerfiles("src/**.h")
    add_includedirs("src")
    -- Resolve from this module's xmake file; a workspace-level build cache can
    -- otherwise point the generated PCH wrapper at an unrelated native/src.
    set_pcxxheader(path.join(os.scriptdir(), "src", "pch.h"))
