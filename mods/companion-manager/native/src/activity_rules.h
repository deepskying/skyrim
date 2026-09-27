#pragma once
#include <algorithm>
#include <cmath>
#include <tuple>
#include <nlohmann/json.hpp>
namespace companion::activity {
using json = nlohmann::json;
inline json Defaults() {
    return {{"loot",true},{"corpses",true},{"ground",true},{"containers",false},
            {"radius",40},{"minValue",20},{"minRatio",5},{"categories",255},
            {"sell",true},{"outfits",true},{"outfitHours",12},{"requests",true},
            {"helmet",false}};
}
// A save written before a key existed would fail the exact-shape check below and take the whole
// record down with it, so missing keys are filled with their schema default before validation. The
// default is always the pre-update behaviour, which is why it lives here and not at the call sites.
inline void Upgrade(json &v) {
    if (!v.is_object()) return;
    const json defaults = Defaults();
    for (auto it = defaults.begin(); it != defaults.end(); ++it)
        if (!v.contains(it.key())) v[it.key()] = it.value();
}
inline bool Valid(const json& v) {
    if (!v.is_object() || v.size()!=Defaults().size()) return false;
    for (auto k : {"loot","corpses","ground","containers","sell","outfits","requests","helmet"})
        if (!v.contains(k)||!v[k].is_boolean()) return false;
    for (auto [k,lo,hi] : {std::tuple{"radius",5,60}, {"minValue",0,10000},
                           {"minRatio",0,1000},{"categories",0,255},{"outfitHours",1,72}})
        if (!v.contains(k)||!v[k].is_number_integer()||v[k]<lo||v[k]>hi) return false;
    return true;
}
inline int Fits(float capacity,float carried,float unit,int available) {
    if (!std::isfinite(capacity)||!std::isfinite(carried)||!std::isfinite(unit)||unit<0||available<=0) return 0;
    const double free=static_cast<double>(capacity)-carried;
    if (free<0) return 0;
    if (unit==0) return available;
    return static_cast<int>(std::min<double>(available,std::floor(free/unit)));
}
inline bool Worth(int category,int value,float weight,const json& p) {
    if (!(p.at("categories").get<int>()&category)) return false;
    if (category==8) return true; // currency / gems
    return value>=p.at("minValue").get<int>() &&
           (weight<=0 || value/weight>=p.at("minRatio").get<int>());
}
inline int SaleCount(int available,int price,int merchantGold) {
    return available>0 && price>0 && merchantGold>0 ? (std::min)(available,merchantGold/price) : 0;
}
inline bool CanRun(bool active,bool waiting,bool combat,bool scene,bool loaded) {
    return active&&!waiting&&!combat&&!scene&&loaded;
}
}
