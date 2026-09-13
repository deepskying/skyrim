#pragma once
#include <cstdint>
#include <cstring>
#include <istream>
#include <optional>
#include <vector>

namespace workshop_migration {
// SKSE Serialization.cpp v1: 20-byte file header, 12-byte plugin/chunk headers.
// Read-only import; never rewrite an existing save. Bound counts before allocating.
inline std::optional<std::vector<std::uint32_t>> ReadLegacyQueue(std::istream& in)
{
    auto word = [&]() { std::uint32_t v=0; in.read(reinterpret_cast<char*>(&v),4); return v; };
    char magic[4]{}; in.read(magic,4);
    if (std::memcmp(magic,"SKSE",4)!=0 || word()!=1) return {};
    word(); word(); const auto plugins=word();
    if (!in || plugins>4096) return {};
    std::optional<std::vector<std::uint32_t>> result;
    for (std::uint32_t p=0;p<plugins;++p) {
        const auto uid=word(), chunks=word(), size=word();
        if (!in || chunks>65536 || size>512U*1024U*1024U) return {};
        if (uid!=0x4D415151) { in.ignore(size); if(!in)return {}; continue; }
        std::uint32_t used=0;
        for (std::uint32_t c=0;c<chunks;++c) {
            if(size-used<12)return {};
            const auto type=word(), version=word(), length=word(); used+=12;
            if(!in || length>size-used)return {};
            if(type==0x51554555 && version==1 && length>=8 && length<=264 && length%4==0) {
                std::vector<std::uint32_t> values(length/4);
                in.read(reinterpret_cast<char*>(values.data()),length);
                if (!in || values[0]>1 || values[1]!=values.size()-2) return {};
                result=std::move(values);
            } else in.ignore(length);
            if(!in)return {}; used+=length;
        }
        if(used!=size)return {};
    }
    return result;
}
}
