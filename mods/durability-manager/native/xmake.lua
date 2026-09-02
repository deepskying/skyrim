set_xmakever("2.8.2")

includes("../../../reference/example-skse-plugin/lib/commonlibsse-ng")

set_project("DurabilityManager")
set_version("0.1.0")
set_languages("c++23")
set_warnings("allextra")
set_policy("package.requires_lock", true)

add_requires("nlohmann_json")

add_rules("mode.release", "mode.debug")
add_rules("plugin.vsxmake.autoupdate")

target("DurabilityManager")
    add_deps("commonlibsse-ng")
    add_packages("nlohmann_json")
    add_cxxflags("/utf-8")
    add_rules("commonlibsse-ng.plugin", {
        name = "DurabilityManager",
        author = "linos",
        description = "Weapon and armor durability with Prisma UI"
    })
    add_files("src/**.cpp")
    add_headerfiles("src/**.h")
    add_includedirs("src")
    set_pcxxheader("src/pch.h")
