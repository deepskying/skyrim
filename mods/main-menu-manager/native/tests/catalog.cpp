// Read-only integration check using the exact catalog code linked into the DLL.
#include "library.h"
#include <iostream>

int wmain(int argc, wchar_t** argv) {
    if (argc != 3) { std::cerr << "Usage: MainMenuCatalogCheck <library> <expected-count>\n"; return 2; }
    try {
        unsigned diagnostics = 0;
        const auto themes = mainmenu::scan(argv[1], [&](const std::string& text) {
            ++diagnostics; std::cout << text << '\n';
        });
        const auto expected = std::stoull(argv[2]);
        std::cout << "Usable themes: " << themes.size() << "; expected: " << expected << "; diagnostics: " << diagnostics << '\n';
        return themes.size() == expected && diagnostics == 0 ? 0 : 1;
    } catch (const std::exception& error) { std::cerr << error.what() << '\n'; return 1; }
}
