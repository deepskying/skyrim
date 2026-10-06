#pragma once
#include "soul_pool_rules.h"
#include <span>
#include <utility>
#include <vector>
namespace soul_pool_rules {
struct Material {std::uint32_t form=0;int count=0;};
struct UpgradeOption {std::vector<Material> materials;};
struct Pool {
    int points=0,tier=0,absorbed=0,gold=0,capacity=baseCapacity,upgradeGain=0;
    std::array<UpgradeOption,upgradeOptions> options;
    bool rolled=false;
    void Reset(){*this=Pool{};}
};
inline constexpr std::uint32_t recordVersion=4;
inline constexpr std::size_t maxRecordWords=7+upgradeOptions*(1+maxMaterials*2);
// v3/v4 share the layout; v4 prices materials as 1-10 of each of up to ten kinds.
inline std::vector<std::uint32_t> EncodePool(const Pool& pool){
    std::vector<std::uint32_t> words{static_cast<std::uint32_t>(pool.options.size()),
        static_cast<std::uint32_t>(pool.points),static_cast<std::uint32_t>(pool.tier),
        static_cast<std::uint32_t>(pool.absorbed),static_cast<std::uint32_t>(pool.gold),
        static_cast<std::uint32_t>(pool.capacity),static_cast<std::uint32_t>(pool.upgradeGain)};
    for(const auto& option:pool.options){
        words.push_back(static_cast<std::uint32_t>(option.materials.size()));
        for(const auto& material:option.materials){words.push_back(material.form);words.push_back(static_cast<std::uint32_t>(material.count));}
    }
    return words;
}
// Unresolvable materials invalidate the plans, but keep the capacity and pending gain.
template<class Resolve>
inline bool DecodePool(std::uint32_t version,std::span<const std::uint32_t> words,Pool& output,Resolve resolve){
    if(version<1||version>recordVersion||words.size()<6||words.size()>maxRecordWords)return false;
    Pool restored;
    restored.points=static_cast<int>(words[1]);restored.tier=static_cast<int>(words[2]);
    restored.absorbed=static_cast<int>(words[3]);restored.gold=static_cast<int>(words[4]);
    if(restored.tier<0||restored.tier>maxTier)return false;
    if(version>=3){
        if(words.size()<9)return false;
        restored.capacity=static_cast<int>(words[5]);restored.upgradeGain=static_cast<int>(words[6]);
        if(restored.upgradeGain<0||restored.upgradeGain>maxUpgrade)return false;
    }else restored.capacity=LegacyCapacity(restored.tier);
    if(!ValidPool(restored.points,restored.tier,restored.absorbed,restored.gold,restored.capacity))return false;
    // v1/v2 reroll the gain; v3 keeps its quoted gain but replaces the old material budget.
    bool valid=version==recordVersion&&restored.upgradeGain>=minUpgrade&&words[0]==upgradeOptions;
    std::size_t cursor=7;
    for(std::size_t index=0;index<upgradeOptions&&valid;++index){
        if(cursor>=words.size()){valid=false;break;}
        const auto count=words[cursor++];
        if(count<1||count>maxMaterials||count*2>words.size()-cursor){valid=false;break;}
        for(std::size_t i=0;i<count;++i){
            std::uint32_t id=0;
            const int quantity=static_cast<int>(words[cursor+1]);
            if(!resolve(words[cursor],id)||!id||quantity<=0||quantity>maxMaterialCount){valid=false;break;}
            restored.options[index].materials.push_back({id,quantity});cursor+=2;
        }
    }
    restored.rolled=valid&&cursor==words.size();
    if(!restored.rolled)for(auto& option:restored.options)option.materials.clear();
    output=std::move(restored);
    return true;
}
}
