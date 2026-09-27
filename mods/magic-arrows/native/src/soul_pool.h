#pragma once
#include "soul_pool_rules.h"
#include "runtime_binding.h"
#include "crafting.h"
#include <random>
namespace soul_pool {
using json=nlohmann::json;
struct Material {RE::FormID form=0;int count=0;};
struct Pool {
    int points=0,tier=0,absorbed=0,gold=0;
    std::vector<Material> next;
    bool rolled=false;
    void Reset(){points=0;tier=0;absorbed=0;gold=0;next.clear();rolled=false;}
};
inline Pool pool;
inline bool available=false,enabled=true;
inline std::vector<std::pair<RE::FormID,std::uint64_t>> banked;
inline std::uint64_t epoch=0;
inline int Capacity(){return soul_pool_rules::Capacity(pool.tier);}
inline RE::TESBoundObject* Bound(RE::FormID id){return RE::TESForm::LookupByID<RE::TESBoundObject>(id);}
inline bool AlreadyBanked(RE::Actor* victim){
    for(const auto& entry:banked)if(entry.first==victim->GetFormID()&&entry.second==epoch)return true;
    return false;
}
inline void MarkBanked(RE::Actor* victim){
    std::erase_if(banked,[&](const auto& entry){return entry.second!=epoch;});
    if(banked.size()>=256)banked.erase(banked.begin());
    banked.emplace_back(victim->GetFormID(),epoch);
}
// Returns true when the soul went into the pool, so the caller can report the vanilla
// capture as successful and still play its sound and visuals.
inline bool Bank(RE::Actor* victim){
    if(!enabled||!available||!victim)return false;
    const int value=soul_pool_rules::SoulValue(static_cast<int>(victim->GetSoulSize()));
    if(value<=0)return false;
    if(AlreadyBanked(victim))return true;
    if(!soul_pool_rules::Accepts(pool.points,Capacity(),value))return false;
    pool.points+=value;pool.absorbed+=value;MarkBanked(victim);
    logger::info("Soul pool absorbed soul={} points={}/{} victim={:08X}",value,pool.points,Capacity(),victim->GetFormID());
    return true;
}
inline std::vector<RE::TESBoundObject*> Candidates(){
    std::vector<RE::TESBoundObject*> list;auto* data=RE::TESDataHandler::GetSingleton();if(!data)return list;
    for(auto* item:data->GetFormArray<RE::IngredientItem>())
        if(item&&!item->IsDeleted()&&!item->IsIgnored()&&item->GetGoldValue()>=5)list.push_back(item);
    if(pool.tier>=2)
        for(auto id:soul_pool_rules::emptyGems)if(auto* gem=RE::TESForm::LookupByID<RE::TESSoulGem>(id))list.push_back(gem);
    return list;
}
inline void RollNext(){
    pool.next.clear();pool.gold=soul_pool_rules::UpgradeGold(pool.tier);pool.rolled=true;
    auto list=Candidates();if(list.empty()){logger::warn("Soul pool upgrade roll found no materials");return;}
    std::mt19937 rng{static_cast<std::uint32_t>(GetTickCount64())^static_cast<std::uint32_t>(pool.tier*2654435761u)};
    const int kinds=std::min<int>(soul_pool_rules::UpgradeKinds(pool.tier),static_cast<int>(list.size()));
    std::vector<std::size_t> picked;
    for(int i=0;i<kinds;++i){
        std::size_t index=0;bool unique=false;
        for(int attempt=0;attempt<32&&!unique;++attempt){
            index=std::uniform_int_distribution<std::size_t>(0,list.size()-1)(rng);
            unique=std::find(picked.begin(),picked.end(),index)==picked.end();
        }
        if(!unique)continue;
        picked.push_back(index);
        pool.next.push_back({list[index]->GetFormID(),soul_pool_rules::UpgradeCount(pool.tier,static_cast<int>(rng()))});
    }
    logger::info("Soul pool tier={} next upgrade needs {} material kind(s), {} gold",pool.tier,pool.next.size(),pool.gold);
}
inline void EnsureRolled(){if(enabled&&!pool.rolled)RollNext();}
inline json State(RE::PlayerCharacter* player){
    const int capacity=Capacity();
    json materials=json::array();
    for(const auto& material:pool.next){
        auto* item=Bound(material.form);
        materials.push_back({{"id",material.form},{"name",item?crafting::Name(item):"来源缺失的材料"},{"count",material.count},{"owned",player&&item?crafting::Count(player,item):0}});
    }
    json gems=json::array();
    for(int level=1;level<=5;++level){
        const auto cost=soul_pool_rules::GemCost(level);auto* gem=Bound(soul_pool_rules::filledGems[static_cast<std::size_t>(level-1)]);
        gems.push_back({{"level",level},{"name",gem?crafting::Name(gem):"灵魂石"},{"points",cost.points},{"gold",cost.gold},{"id",soul_pool_rules::filledGems[static_cast<std::size_t>(level-1)]},
            {"can",soul_pool_rules::Convertible(pool.points,player?crafting::Count(player,Bound(0xF)):0,cost)}});
    }
    {const auto cost=soul_pool_rules::BlackGemCost();auto* gem=Bound(soul_pool_rules::filledBlackGem);
        gems.push_back({{"level",6},{"name",gem?crafting::Name(gem):"黑色灵魂石"},{"points",cost.points},{"gold",cost.gold},{"id",soul_pool_rules::filledBlackGem},
            {"can",soul_pool_rules::Convertible(pool.points,player?crafting::Count(player,Bound(0xF)):0,cost)}});}
    json deposit=json::array();
    if(player){
        for(auto& [object,value]:player->GetInventory()){
            auto* item=object?object->As<RE::TESBoundObject>():nullptr;if(!item||value.first<=0||value.second->IsQuestObject())continue;
            const auto id=item->GetFormID();
            int points=0;
            for(std::size_t i=0;i<soul_pool_rules::filledGems.size();++i)if(soul_pool_rules::filledGems[i]==id)points=static_cast<int>(i)+1;
            if(id==soul_pool_rules::filledBlackGem)points=5;
            if(points<=0)continue;
            deposit.push_back({{"id",id},{"name",crafting::Name(item)},{"count",value.first},{"points",points},{"room",std::max(0,(capacity-pool.points)/points)}});
        }
    }
    return {{"available",available},{"enabled",enabled},{"points",pool.points},{"capacity",capacity},{"tier",pool.tier},{"absorbed",pool.absorbed},
        {"upgradeGold",pool.gold},{"materials",materials},{"gems",gems},{"deposit",deposit},
        {"gold",player?crafting::Count(player,Bound(0xF)):0}};
}
// The bottom-left HUD only needs the readout, so it never walks the inventory.
inline json Hud(){return {{"enabled",enabled&&available},{"points",pool.points},{"capacity",Capacity()},{"tier",pool.tier}};}
inline bool Upgrade(RE::PlayerCharacter* player){
    EnsureRolled();if(!player)throw std::runtime_error("尚未准备好");
    for(const auto& material:pool.next){auto* item=Bound(material.form);if(!item||crafting::Count(player,item)<material.count)throw std::runtime_error("扩容材料不足");}
    if(crafting::Count(player,Bound(0xF))<pool.gold)throw std::runtime_error("金币不足");
    for(const auto& material:pool.next)player->RemoveItem(Bound(material.form),material.count,RE::ITEM_REMOVE_REASON::kRemove,nullptr,nullptr);
    if(pool.gold>0)player->RemoveItem(Bound(0xF),pool.gold,RE::ITEM_REMOVE_REASON::kRemove,nullptr,nullptr);
    ++pool.tier;RollNext();
    logger::info("Soul pool expanded tier={} capacity={}",pool.tier,Capacity());
    return true;
}
struct Request {int level=0;int count=0;};
// One panel confirm can ask for several gem types at once; every line is clamped to what
// the pool and the purse can still pay for after the previous lines.
inline json Convert(RE::PlayerCharacter* player,const std::vector<Request>& requests){
    json result={{"gems",0},{"points",0},{"gold",0}};
    EnsureRolled();if(!player||requests.empty())return result;
    int points=pool.points,gold=crafting::Count(player,Bound(0xF)),spentPoints=0,spentGold=0,gems=0;
    std::vector<std::pair<RE::FormID,int>> outputs;
    for(const auto& request:requests){
        if(request.count<=0)continue;
        const bool black=request.level==6;
        const auto cost=black?soul_pool_rules::BlackGemCost():soul_pool_rules::GemCost(request.level);
        const auto id=black?soul_pool_rules::filledBlackGem:(request.level>=1&&request.level<=5?soul_pool_rules::filledGems[static_cast<std::size_t>(request.level-1)]:0);
        if(!id||cost.points<=0)continue;
        const int affordable=std::min(request.count,soul_pool_rules::Convertible(points,gold,cost));
        if(affordable<=0)continue;
        points-=cost.points*affordable;gold-=cost.gold*affordable;
        spentPoints+=cost.points*affordable;spentGold+=cost.gold*affordable;gems+=affordable;
        outputs.emplace_back(id,affordable);
    }
    if(gems<=0)return result;
    try{
        if(spentGold>0)player->RemoveItem(Bound(0xF),spentGold,RE::ITEM_REMOVE_REASON::kRemove,nullptr,nullptr);
        pool.points-=spentPoints;
        for(const auto& [id,count]:outputs)player->AddObjectToContainer(Bound(id),nullptr,count,nullptr);
    }catch(...){
        pool.points+=spentPoints;
        if(spentGold>0)player->AddObjectToContainer(Bound(0xF),nullptr,spentGold,nullptr);
        throw;
    }
    logger::info("Soul pool converted gems={} points={} gold={} left={}/{}",gems,spentPoints,spentGold,pool.points,Capacity());
    return {{"gems",gems},{"points",spentPoints},{"gold",spentGold}};
}
inline int Deposit(RE::PlayerCharacter* player,RE::FormID form,int count){
    EnsureRolled();if(!player||count<=0)return 0;
    auto* gem=Bound(form);if(!gem)return 0;
    int value=0;
    for(std::size_t i=0;i<soul_pool_rules::filledGems.size();++i)if(soul_pool_rules::filledGems[i]==form)value=static_cast<int>(i)+1;
    if(form==soul_pool_rules::filledBlackGem)value=5;
    if(value<=0)throw std::runtime_error("只能存入填好的灵魂石");
    const int owned=crafting::Count(player,gem);
    const int room=(Capacity()-pool.points)/value;
    const int moved=std::min({count,owned,room});
    if(moved<=0)return 0;
    player->RemoveItem(gem,moved,RE::ITEM_REMOVE_REASON::kRemove,nullptr,nullptr);
    pool.points+=value*moved;pool.absorbed+=value*moved;
    logger::info("Soul pool deposited gem={:08X} count={} points={}/{}",form,moved,pool.points,Capacity());
    return moved;
}
inline void Reset(){pool.Reset();banked.clear();epoch=runtime_binding::generation.load();}
inline void Save(SKSE::SerializationInterface* api){
    if(!api)return;
    std::vector<std::uint32_t> words{0u,static_cast<std::uint32_t>(pool.points),static_cast<std::uint32_t>(pool.tier),static_cast<std::uint32_t>(pool.absorbed),
        static_cast<std::uint32_t>(pool.gold),static_cast<std::uint32_t>(pool.next.size())};
    for(const auto& material:pool.next){words.push_back(material.form);words.push_back(static_cast<std::uint32_t>(material.count));}
    if(!api->WriteRecord(soul_pool_rules::record,1,words.data(),static_cast<std::uint32_t>(words.size()*sizeof(std::uint32_t))))logger::error("Soul pool save failed");
}
inline void Revert(SKSE::SerializationInterface*){Reset();}
inline bool LoadRecord(SKSE::SerializationInterface* api,std::uint32_t type,std::uint32_t version,std::uint32_t length){
    if(type!=soul_pool_rules::record)return false;
    const std::size_t maxWords=6+soul_pool_rules::maxMaterials*2;
    if(version!=1||length<6*4||length>maxWords*4||length%4)return true;
    std::vector<std::uint32_t> words(length/4);
    if(api->ReadRecordData(words.data(),length)!=length)return true;
    const std::size_t kinds=words[5];
    if(kinds>soul_pool_rules::maxMaterials||words.size()!=6+kinds*2)return true;
    if(!soul_pool_rules::ValidPool(static_cast<int>(words[1]),static_cast<int>(words[2]),static_cast<int>(words[3]),static_cast<int>(words[4]),kinds))return true;
    Pool restored;
    restored.points=static_cast<int>(words[1]);restored.tier=static_cast<int>(words[2]);restored.absorbed=static_cast<int>(words[3]);
    restored.gold=static_cast<int>(words[4]);restored.rolled=true;
    bool valid=true;
    for(std::size_t i=0;i<kinds;++i){
        RE::FormID id=0;
        if(!api->ResolveFormID(words[6+i*2],id)||!id||!Bound(id)){valid=false;break;}
        const int count=static_cast<int>(words[7+i*2]);
        if(count<=0||count>1000){valid=false;break;}
        restored.next.push_back({id,count});
    }
    pool=std::move(restored);
    if(!valid){pool.rolled=false;pool.next.clear();logger::warn("Soul pool upgrade requirement could not be resolved; it will be rolled again");}
    pool.points=std::min(pool.points,Capacity());
    logger::info("Soul pool loaded points={}/{} tier={} absorbed={}",pool.points,Capacity(),pool.tier,pool.absorbed);
    return true;
}
}
