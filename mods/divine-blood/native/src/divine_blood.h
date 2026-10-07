#pragma once
#include "catalog.h"
#include "rules.h"
#include <SKSE/Events.h>
namespace divine_blood {
using json=nlohmann::json;
inline std::array<std::uint32_t,16> absorbed{};
struct Pricing{int soul=10,alchemy=10,units=1;};
inline std::array<Pricing,16> prices{};
inline std::unordered_set<std::uint64_t> handled;
inline std::atomic<std::uint64_t> epoch{1};
inline std::atomic<std::uint64_t> saveEpoch{1};
inline constexpr std::uint32_t record=0x44424C44;
inline RE::AlchemyItem* Item(std::size_t index){auto* data=RE::TESDataHandler::GetSingleton();return data?data->LookupForm<RE::AlchemyItem>(recipes[index].form,"The Blood of Divines.esp"):nullptr;}
inline int Units(RE::IngredientItem* item,std::size_t index){
    if(!item)return 0;
    int strongest=0;
    for(auto* e:item->effects){auto* effect=e?e->baseEffect:nullptr;
        if(!effect||effect->data.flags.any(RE::EffectSetting::EffectSettingData::Flag::kDetrimental))continue;
        bool matches=false;
        for(int av:recipes[index].actorValues)if(av>=0&&(static_cast<int>(effect->data.primaryAV)==av||static_cast<int>(effect->data.secondaryAV)==av))matches=true;
        if(!matches)continue;
        const auto flags=effect->data.flags;
        const auto duration=flags.any(RE::EffectSetting::EffectSettingData::Flag::kNoDuration)?0:e->effectItem.duration;
        strongest=std::max(strongest,divine_blood_rules::IngredientPoints(e->effectItem.magnitude,duration,prices[index].units,flags.any(RE::EffectSetting::EffectSettingData::Flag::kNoMagnitude)));
    }return strongest;
}

inline json State(RE::PlayerCharacter* player,bool inventory){
    json cards=json::array(),materials=json::array();bool installed=true;
    for(std::size_t i=0;i<recipes.size();++i){const auto& r=recipes[i];auto* item=Item(i);installed&=item!=nullptr;
        cards.push_back({{"key",r.key},{"name",r.name},{"gain",r.gain},{"absorbed",absorbed[i]},
            {"soulCost",divine_blood_rules::Cost(prices[i].soul,absorbed[i])},{"alchemyCost",divine_blood_rules::Cost(prices[i].alchemy,absorbed[i])},{"owned",player&&item?crafting::Count(player,item):0}});
    }
    if(player&&inventory)for(auto& [object,value]:player->GetInventory()){
        auto* item=object?object->As<RE::IngredientItem>():nullptr;
        if(!item||value.first<=0||!value.second||value.second->IsQuestObject())continue;
        json points=json::object();for(std::size_t i=0;i<recipes.size();++i)if(auto n=Units(item,i);n>0)points[recipes[i].key]=n;
        if(!points.empty())materials.push_back({{"id",item->GetFormID()},{"name",crafting::Name(item)},{"count",value.first},{"points",points}});
    }
    return {{"available",installed&&soul_pool::enabled&&soul_pool::available},{"epoch",epoch.load()},{"cards",cards},{"materials",materials}};
}
inline int Craft(RE::PlayerCharacter* player,const json& q){
    const auto request=q.at("requestID").get<std::uint64_t>();
    if(!request||q.at("epoch").get<std::uint64_t>()!=epoch||handled.contains(request))throw std::runtime_error("炼制请求已失效，请刷新");
    if(handled.size()>=4096)throw std::runtime_error("请关闭工坊并重新打开后炼制");
    handled.insert(request); // A retry may not spend twice, even after an exception.
    if(!player||player->IsDead()||!soul_pool::enabled||!soul_pool::available)throw std::runtime_error("灵魂池尚未就绪");
    if(!crafting_access::Nearby(player).alchemy)throw std::runtime_error("请靠近炼金台后炼制神之血");
    const auto key=q.at("key").get<std::string>();std::size_t index=0;
    while(index<recipes.size()&&key!=recipes[index].key)++index;
    if(index==recipes.size()||!Item(index))throw std::runtime_error("神血物品未加载");
    const int ac=divine_blood_rules::Cost(prices[index].alchemy,absorbed[index]),sc=divine_blood_rules::Cost(prices[index].soul,absorbed[index]);
    if(q.at("alchemyCost")!=ac||q.at("soulCost")!=sc)throw std::runtime_error("神血费用已变化，请重新确认");
    const auto& rows=q.at("materials");if(!rows.is_array()||rows.empty()||rows.size()>128)throw std::runtime_error("请选择炼金材料");
    struct Selected{RE::IngredientItem* item;int count;int before;};std::vector<Selected> selected;
    std::unordered_set<RE::FormID> seen;std::int64_t points=0;
    const auto inventory=player->GetInventory();
    for(const auto& row:rows){
        const auto id=row.at("id").get<RE::FormID>();
        if(!row.at("count").is_number_integer())throw std::runtime_error("材料数量必须为整数");
        const auto count=row.at("count").get<std::int64_t>();
        auto* item=RE::TESForm::LookupByID<RE::IngredientItem>(id);auto it=inventory.find(item);const int units=Units(item,index);
        if(!seen.insert(id).second||count<=0||count>INT_MAX||units<=0||it==inventory.end()||!it->second.second||it->second.second->IsQuestObject()||it->second.first<count)throw std::runtime_error("材料不足、受任务保护或不适用于当前神血");
        if(!row.contains("pointsPerItem")||row.at("pointsPerItem")!=units)throw std::runtime_error("材料填充点数已变化，请刷新后重新确认");
        points+=count*units;if(points>soul_pool::Capacity())throw std::runtime_error("所选材料超出炼金池容量");
        selected.push_back({item,static_cast<int>(count),it->second.first});
    }
    const int output=divine_blood_rules::Output(points,soul_pool::Capacity(),soul_pool::pool.points,ac,sc);
    if(output<=0)throw std::runtime_error("两池点数不足一份，材料未消耗");
    if(q.at("output")!=output)throw std::runtime_error("可炼制数量已变化，请重新确认");
    auto* product=Item(index);const int before=crafting::Count(player,product);
    if(before>INT_MAX-output)throw std::runtime_error("神血库存数量超限");
    try{
        for(auto& s:selected){player->RemoveItem(s.item,s.count,RE::ITEM_REMOVE_REASON::kRemove,nullptr,nullptr);
            if(crafting::Count(player,s.item)!=s.before-s.count)throw std::runtime_error("材料扣除失败，炼制取消");}
        player->AddObjectToContainer(product,nullptr,output,nullptr);
        if(crafting::Count(player,product)!=before+output)throw std::runtime_error("成品入包失败，炼制取消");
    }catch(...){
        const int added=crafting::Count(player,product)-before;if(added>0)player->RemoveItem(product,added,RE::ITEM_REMOVE_REASON::kRemove,nullptr,nullptr);
        for(auto& s:selected){const int removed=s.before-crafting::Count(player,s.item);if(removed>0)player->AddObjectToContainer(s.item,nullptr,removed,nullptr);}
        throw;
    }
    soul_pool::pool.points-=output*sc;
    logger::info("Divine blood crafted {} count={} alchemy={} soul={} absorbed={}",key,output,points,output*sc,absorbed[index]);
    return output;
}
inline void Reset(){absorbed.fill(0);handled.clear();++epoch;++saveEpoch;}
inline void Save(SKSE::SerializationInterface* api){if(api&&!api->WriteRecord(record,1,absorbed.data(),sizeof(absorbed)))logger::error("Divine blood counts save failed");}
inline bool Load(SKSE::SerializationInterface* api,std::uint32_t type,std::uint32_t version,std::uint32_t length){
    if(type!=record)return false;
    std::array<std::uint32_t,16> restored{};
    if(api&&version==1&&length==sizeof(restored)&&api->ReadRecordData(restored.data(),length)==length)absorbed=restored;
    return true;
}
class Absorption final:public RE::BSTEventSink<SKSE::ModCallbackEvent>{
    RE::BSEventNotifyControl ProcessEvent(const SKSE::ModCallbackEvent* event,RE::BSTEventSource<SKSE::ModCallbackEvent>*)override{
        if(!event||event->eventName!="DivineBloodAbsorbed"||event->numArg!=1.f)return RE::BSEventNotifyControl::kContinue;
        if(event->sender!=RE::PlayerCharacter::GetSingleton())return RE::BSEventNotifyControl::kContinue;
        const std::string key=event->strArg.c_str();const auto generation=saveEpoch.load();
        if(auto* tasks=SKSE::GetTaskInterface())tasks->AddTask([key,generation]{
            if(generation!=saveEpoch.load())return;
            for(std::size_t i=0;i<recipes.size();++i)if(key==recipes[i].key&&absorbed[i]<UINT32_MAX){++absorbed[i];break;}
        });
        return RE::BSEventNotifyControl::kContinue;
    }
};
inline Absorption absorption;
inline void Init(){
    const auto path=std::filesystem::path(REL::Module::get().filePath().data()).parent_path()/"Data/SKSE/Plugins/DivineBlood.ini";
    for(std::size_t i=0;i<recipes.size();++i){std::string key=recipes[i].key;std::wstring section(key.begin(),key.end());
        prices[i]={std::clamp(static_cast<int>(GetPrivateProfileIntW(section.c_str(),L"SoulCost",10,path.c_str())),1,1000000),
            std::clamp(static_cast<int>(GetPrivateProfileIntW(section.c_str(),L"AlchemyCost",10,path.c_str())),1,1000000),
            std::clamp(static_cast<int>(GetPrivateProfileIntW(section.c_str(),L"PointsPerIngredient",1,path.c_str())),1,1000000)};
    }
    if(auto* events=SKSE::GetModCallbackEventSource())events->AddEventSink(&absorption);
}
}
