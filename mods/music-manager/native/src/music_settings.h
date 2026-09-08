#pragma once
#include <nlohmann/json.hpp>
#include <cmath>
#include <stdexcept>
#include <array>
#include <string>
namespace music {
struct PlaybackSettings {
    bool pauseWithGame = true, followMaster = true;
    double fadeSeconds = 1.2, combatFadeSeconds = .35, sceneDelay = 2, combatExitDelay = 3, dayStart = 6, dayEnd = 20;
    nlohmann::json json() const {
        return {{"pauseWithGame",pauseWithGame},{"followMaster",followMaster},{"fadeSeconds",fadeSeconds},{"combatFadeSeconds",combatFadeSeconds},{"sceneDelay",sceneDelay},{"combatExitDelay",combatExitDelay},{"dayStart",dayStart},{"dayEnd",dayEnd}};
    }
    static PlaybackSettings parse(const nlohmann::json& j) {
        if (!j.is_object()) throw std::runtime_error("播放设置格式错误");
        PlaybackSettings s;
        s.pauseWithGame = j.value("pauseWithGame",true); s.followMaster = j.value("followMaster",true);
        auto number = [&](const char* name, double fallback, double low, double high) {
            auto v = j.value(name,fallback);
            if (!std::isfinite(v) || v < low || v > high) throw std::runtime_error("播放参数超出范围");
            return v;
        };
        s.fadeSeconds = number("fadeSeconds",1.2,0,10); s.combatFadeSeconds = number("combatFadeSeconds",.35,0,5);
        s.sceneDelay = number("sceneDelay",2,0,15); s.combatExitDelay = number("combatExitDelay",3,0,15);
        s.dayStart = number("dayStart",6,0,23); s.dayEnd = number("dayEnd",20,1,24);
        if (s.dayStart >= s.dayEnd) throw std::runtime_error("白天开始时间必须早于结束时间");
        return s;
    }
};
struct Hotkey {
    unsigned scanCode = 0x32;
    bool shift = true, ctrl = false, alt = false;
    static std::string keyName(unsigned scan) {
        constexpr std::array<unsigned,26> letters{0x1e,0x30,0x2e,0x20,0x12,0x21,0x22,0x23,0x17,0x24,0x25,0x26,0x32,0x31,0x18,0x19,0x10,0x13,0x1f,0x14,0x16,0x2f,0x11,0x2d,0x15,0x2c};
        for (unsigned i=0;i<letters.size();++i) if (letters[i]==scan) return std::string(1,static_cast<char>('A'+i));
        if (scan>=0x3b && scan<=0x44) return "F"+std::to_string(scan-0x3a);
        if (scan==0x57) return "F11";
        if (scan==0x58) return "F12";
        return {};
    }
    std::string label() const { return std::string(ctrl?"Ctrl + ":"")+(shift?"Shift + ":"")+(alt?"Alt + ":"")+keyName(scanCode); }
    bool matches(unsigned code,bool s,bool c,bool a) const { return code==scanCode && shift==s && ctrl==c && alt==a; }
    nlohmann::json json() const { return {{"scanCode",scanCode},{"shift",shift},{"ctrl",ctrl},{"alt",alt},{"label",label()}}; }
    static Hotkey parse(const nlohmann::json& j) {
        Hotkey h;
        h.scanCode = j.at("scanCode").get<unsigned>();
        h.shift = j.at("shift").get<bool>(); h.ctrl = j.at("ctrl").get<bool>(); h.alt = j.at("alt").get<bool>();
        if (keyName(h.scanCode).empty()) throw std::runtime_error("请选择 A–Z 或 F1–F12；Esc 保留用于关闭面板");
        return h;
    }
};
}
