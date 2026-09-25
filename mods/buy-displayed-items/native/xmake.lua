set_xmakever("2.8.2")
includes("../../../reference/example-skse-plugin/lib/commonlibsse-ng")
set_project("BuyDisplayedItems")
set_version("0.1.0")
set_languages("c++23")
add_rules("mode.release", "mode.debug")

target("BuyDisplayedItems")
    add_deps("commonlibsse-ng")
    add_cxxflags("/utf-8")
    add_rules("commonlibsse-ng.plugin", {
        name = "BuyDisplayedItems",
        author = "linos",
        description = "Purchase merchant-owned items displayed in shops and inns"
    })
    add_files("src/main.cpp")
    add_headerfiles("src/purchase.h")

target("PurchaseTests")
    set_kind("binary")
    set_default(false)
    add_cxxflags("/utf-8")
    add_includedirs("src")
    add_files("tests/purchase.cpp")
