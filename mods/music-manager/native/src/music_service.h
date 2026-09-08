#pragma once
#include "music_rules.h"
#include <nlohmann/json.hpp>
#include <filesystem>
#include <memory>

namespace music {
class Service {
public:
    Service(std::filesystem::path root, std::filesystem::path settings);
    ~Service();
    void environment(Environment value);
    void command(nlohmann::json value);
    nlohmann::json snapshot();
    bool enabled() const;
    bool ready() const;
private:
    struct Impl;
    std::unique_ptr<Impl> impl_;
};
}
