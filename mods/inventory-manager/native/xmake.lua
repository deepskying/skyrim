set_xmakever("2.8.2")

includes("../../../reference/example-skse-plugin/lib/commonlibsse-ng")

set_project("InventoryManager")
set_version("0.1.3")
set_languages("c++23")
set_warnings("allextra")
set_policy("package.requires_lock", true)

add_requires("nlohmann_json")

add_rules("mode.release", "mode.debug")
add_rules("plugin.vsxmake.autoupdate")

target("InventoryManager")
    add_deps("commonlibsse-ng")
    add_packages("nlohmann_json")
    add_rules("commonlibsse-ng.plugin", {
        name = "InventoryManager",
        author = "linos",
        description = "Lightweight Prisma UI inventory and magic manager"
    })
    add_files("src/**.cpp")
    add_headerfiles("src/**.h")
    add_includedirs("src")
    set_pcxxheader("src/pch.h")
