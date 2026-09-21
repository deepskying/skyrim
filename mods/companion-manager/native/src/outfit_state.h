#pragma once
#include "state_rules.h"
#include <charconv>
#include <format>
#include <optional>
#include <unordered_set>

namespace companion::outfit {
using json=nlohmann::json;
template<class Resolver>
std::optional<std::string> RemapKey(const json& value,Resolver resolve) {
    if(!value.is_string()) throw std::runtime_error("Invalid wardrobe key");
    const auto key=value.get<std::string>();
    if(key.size()!=22||key[8]!=':'||key[17]!=':') throw std::runtime_error("Invalid wardrobe key");
    auto parse=[](std::string_view v){std::uint32_t n=0;auto p=std::from_chars(v.data(),v.data()+v.size(),n,16);
        if(p.ec!=std::errc{}||p.ptr!=v.data()+v.size())throw std::runtime_error("Invalid wardrobe ID");return n;};
    const auto base=parse(std::string_view(key).substr(0,8)),owner=parse(std::string_view(key).substr(9,8)),uid=parse(std::string_view(key).substr(18,4));
    std::uint32_t b=0,o=0;
    if(!base||!resolve(base,b)||(owner&&!resolve(owner,o))) return std::nullopt;
    return std::format("{:08X}:{:08X}:{:04X}",b,o,uid);
}
template<class Resolver>
void RemapPresets(json& presets,Resolver resolve) {
    if(!presets.is_array()||presets.size()>64)throw std::runtime_error("Invalid outfit presets");
    std::unordered_set<unsigned> ids;
    for(auto& p:presets) {
        if(!rules::Integer(p.at("id"),1,1000000)||!ids.insert(p["id"].get<unsigned>()).second||
           !p.at("name").is_string()||p["name"].get_ref<const std::string&>().size()>120||
           !p.at("items").is_array()||p["items"].size()>64)throw std::runtime_error("Invalid outfit preset");
        for(auto& item:p["items"]) {
            if(!rules::Integer(item.at("form"),0,0xFFFFFFFF)||!rules::Integer(item.at("mask"),1,0xFFFFFFFF)||
               !item.at("name").is_string()||item["name"].get_ref<const std::string&>().size()>4096)throw std::runtime_error("Invalid preset item");
            const auto key=RemapKey(item.at("key"),resolve);
            std::uint32_t mapped=0;resolve(item["form"].get<std::uint32_t>(),mapped);
            item["form"]=mapped;item["key"]=key.value_or("00000000:00000000:0000");
        }
    }
}
}
