#include "miniaudio.h"
#include <filesystem>
#include <iostream>
#include <vector>
#include <fstream>
int wmain(int argc, wchar_t** argv) {
    if (argc != 2) return 2;
    int failures = 0, count = 0;
    std::ofstream failed("audio-failures.txt", std::ios::binary | std::ios::trunc);
    for (const auto& entry : std::filesystem::recursive_directory_iterator(argv[1])) {
        auto ext = entry.path().extension();
        if (ext != L".mp3" && ext != L".flac" && ext != L".wav") continue;
        ma_decoder decoder{};
        auto config = ma_decoder_config_init(ma_format_f32, 2, 48000);
        auto result = ma_decoder_init_file_w(entry.path().c_str(), &config, &decoder);
        if (result != MA_SUCCESS) { ++failures; auto name = entry.path().u8string(); failed << std::string(name.begin(), name.end()) << '\n'; continue; }
        float buffer[2048]; ma_uint64 read = 0;
        result = ma_decoder_read_pcm_frames(&decoder, buffer, 1024, &read);
        if (read == 0 || (result != MA_SUCCESS && result != MA_AT_END)) { ++failures; auto name = entry.path().u8string(); failed << std::string(name.begin(), name.end()) << '\n'; }
        ma_decoder_uninit(&decoder); ++count;
    }
    std::cout << count << " audio files checked, " << failures << " failures\n";
    return failures || count == 0 ? 1 : 0;
}
