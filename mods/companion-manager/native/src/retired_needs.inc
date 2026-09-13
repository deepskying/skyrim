// Upgrade cleanup only. No needs timers, consumption, requests or penalties are started.
// Keep unresolved actors in the co-save until their own recorded modifiers can be removed.
std::unordered_map<RE::FormID,json> retiredNeeds;

std::unordered_map<RE::FormID,json> ReadRetiredNeeds(const json& data,SKSE::SerializationInterface* serialization)
{
    std::unordered_map<RE::FormID,json> result;
    if(!data.contains("needsActors"))return result;
    const auto& rows=data.at("needsActors");
    if(!rows.is_array()||rows.size()>65)throw std::runtime_error("Invalid retired needs actors");
    for(const auto& row:rows){
        const auto& values=row.at("penalties");
        if(!values.is_array()||values.size()!=3)throw std::runtime_error("Invalid retired needs penalties");
        bool pending=false;
        for(const auto& value:values){
            if(!value.is_number()||!std::isfinite(value.get<float>())||value.get<float>()<0)
                throw std::runtime_error("Invalid retired needs modifier");
            pending|=value.get<float>()>0;
        }
        RE::FormID id=0;
        if(pending&&serialization->ResolveFormID(row.at("actor").get<RE::FormID>(),id)){
            if(!result.emplace(id,values).second)throw std::runtime_error("Duplicate retired needs actor");
        }
    }
    return result;
}

void ClearRetiredNeeds()
{
    const std::array<RE::ActorValue,3> values={RE::ActorValue::kStamina,RE::ActorValue::kMagicka,RE::ActorValue::kSpeedMult};
    for(auto it=retiredNeeds.begin();it!=retiredNeeds.end();){
        auto* actor=Actor(it->first);
        if(!actor){++it;continue;}
        auto* av=actor->AsActorValueOwner();
        for(int i=0;i<3;++i){
            const float amount=it->second[i].get<float>();
            if(amount<=0)continue;
            const float before=av->GetActorValue(values[i]);
            av->RestoreActorValue(RE::ACTOR_VALUE_MODIFIERS::kPermanent,values[i],amount);
            if(i<2){
                const float gain=av->GetActorValue(values[i])-before;
                if(gain>0)av->RestoreActorValue(RE::ACTOR_VALUE_MODIFIERS::kDamage,values[i],-gain);
            }
        }
        logger::info("Removed retired needs modifiers from {:08X}",it->first);
        it=retiredNeeds.erase(it);
    }
}
