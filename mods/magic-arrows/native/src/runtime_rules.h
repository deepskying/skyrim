#pragma once
#include "crafting_plan.h"
#include "sustained_rules.h"
#include <array>
#include <string>
#include <string_view>
#include <cctype>
namespace runtime_rules {
inline constexpr std::array<const char*,12> families{"fire","ice","shock","poison","blood","holy","wind","water","earth","dark","soul","arcane"};
inline int Family(std::string_view s){for(int i=0;i<12;++i)if(s==families[i])return i;return 11;}
inline int Dominant(const std::array<int,12>& score){int best=0,index=11;bool tie=false;for(int i=0;i<12;++i)if(score[i]>best){best=score[i];index=i;tie=false;}else if(score[i]&&score[i]==best)tie=true;return tie?11:index;}
inline int Keyword(std::string text){
    std::transform(text.begin(),text.end(),text.begin(),[](unsigned char c){return static_cast<char>(std::tolower(c));});
    if(text=="magicdamagefire")return 0;if(text=="magicdamagefrost")return 1;if(text=="magicdamageshock")return 2;
    for(auto [word,family]:{std::pair{"poison",3},{"blood",4},{"holy",5},{"sun",5},{"wind",6},{"water",7},{"earth",8},{"shadow",9},{"dark",9},{"soul",10},{"arcane",11}})
        if(text.find(word)!=std::string::npos)return family;
    return -1;
}
inline crafting::Costs Costs(float cost,bool sustained=false,float alchemy=0.f,float enchanting=0.f){
    if(!std::isfinite(cost)||cost<0)throw std::runtime_error("法术费用无效");
    cost=std::min(cost,2000.f)*(sustained?sustained_rules::seconds:1.f);
    return crafting::WithEnchanting(crafting::WithAlchemy({std::clamp(static_cast<int>(std::ceil(std::min(cost,2000.f)/20)),1,100),std::clamp(static_cast<int>(std::ceil(std::min(cost,1000.f)*.5f)),1,500),std::clamp(static_cast<int>(std::ceil(std::min(cost,1000.f)*.25f)),1,250)},alchemy),enchanting);
}
// Source lists are interpreted by type, never by insertion order.
struct SavedRefs {bool occupied=false,marker=false;int spellCount=0,baseCount=0,otherCount=0;};
inline bool Resolvable(SavedRefs r){return r.occupied&&r.marker&&r.spellCount==1&&r.baseCount<=1&&!r.otherCount;}
}
