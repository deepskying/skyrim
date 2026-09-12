#pragma once
#include <Windows.h>
#include <filesystem>
#include <stdexcept>
#include <string>

namespace music {
struct ArchivedTrack {
    std::filesystem::path original, archived;
    std::string name, ticket;
};

// Reject junctions/symlinks as well as lexical escapes before touching a file.
inline std::filesystem::path checkedLibraryPath(const std::filesystem::path& root, const std::filesystem::path& path) {
    namespace fs = std::filesystem;
    const auto base = fs::absolute(root).lexically_normal();
    const auto target = fs::absolute(path).lexically_normal();
    const auto relative = target.lexically_relative(base);
    if (relative.empty() || relative == "." || relative.is_absolute()) throw std::runtime_error("文件不在音乐库内");
    for (const auto& part : relative) if (part == "..") throw std::runtime_error("文件不在音乐库内");
    auto check = [](const fs::path& candidate) {
        const auto attributes = GetFileAttributesW(candidate.c_str());
        if (attributes != INVALID_FILE_ATTRIBUTES && (attributes & FILE_ATTRIBUTE_REPARSE_POINT))
            throw std::runtime_error("不能移动链接目录中的音乐文件");
    };
    // Include ancestors: a substituted library root must not redirect the operation.
    fs::path walking = base.root_path();
    for (const auto& part : base.relative_path()) { walking /= part; check(walking); }
    for (const auto& part : relative) { walking /= part; check(walking); }
    return target;
}

inline ArchivedTrack prepareArchive(const std::filesystem::path& root, const std::filesystem::path& source) {
    namespace fs = std::filesystem;
    const auto original = checkedLibraryPath(root, source);
    if (!fs::is_regular_file(original)) throw std::runtime_error("音乐文件已经不存在");
    const auto base = fs::absolute(root).lexically_normal();
    const auto trash = checkedLibraryPath(root, base / L"_已删除");
    fs::create_directories(trash);
    for (unsigned attempt = 0; attempt < 100; ++attempt) {
        const auto folder = trash / (std::to_wstring(GetTickCount64()) + L"-" + std::to_wstring(attempt));
        checkedLibraryPath(root, folder);
        if (!fs::create_directory(folder)) continue;
        const auto destination = checkedLibraryPath(root, folder / original.lexically_relative(base));
        fs::create_directories(destination.parent_path());
        auto ticket = destination.lexically_relative(base).generic_u8string();
        return {original, destination, {}, std::string(ticket.begin(), ticket.end())};
    }
    throw std::runtime_error("无法创建删除备份目录");
}

inline void moveLibraryFile(const std::filesystem::path& root, const std::filesystem::path& from, const std::filesystem::path& to) {
    const auto source = checkedLibraryPath(root, from), destination = checkedLibraryPath(root, to);
    if (!std::filesystem::is_regular_file(source)) throw std::runtime_error("音乐文件已经不存在");
    if (std::filesystem::exists(destination)) throw std::runtime_error("目标文件已存在，未覆盖原文件");
    // Both paths stay on the library volume; never replace a file or copy/delete.
    if (!MoveFileExW(source.c_str(), destination.c_str(), MOVEFILE_WRITE_THROUGH))
        throw std::runtime_error("无法移动音乐文件（可能仍被其他程序占用），错误码 " + std::to_string(GetLastError()));
}
}
