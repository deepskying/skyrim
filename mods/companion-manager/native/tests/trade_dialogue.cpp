#ifdef NDEBUG
#undef NDEBUG
#endif
#include "check.h"
#include <memory>
namespace RE {
struct TESFaction {};
enum class CONDITIONITEMOBJECT {kSelf,kTarget};
struct FUNCTION_DATA {
    enum class FunctionID {kGetInFaction,kGetPlayerTeammate,kVoiceGate,kQuestGate};
    FunctionID function=FunctionID::kGetInFaction;
    void* params[2]{};
};
struct CONDITION_ITEM_DATA {
    enum class OpCode {kEqualTo,kNotEqualTo};
    struct {float f=1;} comparisonValue;
    struct {bool isOR=false,global=false,usesAliases=false,usePackData=false,swapTarget=false;OpCode opCode=OpCode::kEqualTo;} flags;
    CONDITIONITEMOBJECT object=CONDITIONITEMOBJECT::kSelf;
    FUNCTION_DATA functionData;
};
struct TESConditionItem {TESConditionItem* next=nullptr;CONDITION_ITEM_DATA data;};
}
#include "../src/trade_dialogue.h"
using Fn=RE::FUNCTION_DATA::FunctionID;
bool Evaluate(RE::TESConditionItem* node,RE::TESFaction* vanilla,bool v,bool m,bool t,bool voice,bool quest){
    bool group=false;
    for(;node;node=node->next){
        const auto& d=node->data;
        const bool value=d.functionData.function==Fn::kGetInFaction?(d.functionData.params[0]==vanilla?v:m):
            d.functionData.function==Fn::kGetPlayerTeammate?t:d.functionData.function==Fn::kVoiceGate?voice:quest;
        group|=value;
        if(!d.flags.isOR){if(!group)return false;group=false;}
    }
    return true;
}
int main(){
    RE::TESFaction vanilla,managed;
    RE::TESConditionItem voice,condition,quest;
    voice.data.functionData.function=Fn::kVoiceGate;voice.next=&condition;
    condition.data.functionData.params[0]=&vanilla;condition.next=&quest;
    quest.data.functionData.function=Fn::kQuestGate;
    CHECK(companion::dialogue::ExtendTradeCondition(&condition,false,&vanilla,&managed));
    for(int mask=0;mask<32;++mask){
        const bool v=mask&1,m=mask&2,t=mask&4,a=mask&8,b=mask&16;
        CHECK(Evaluate(&voice,&vanilla,v,m,t,a,b)==(a&&b&&(v||(m&&t))));
    }
    CHECK(!companion::dialogue::ExtendTradeCondition(&condition,false,&vanilla,&managed));
    auto* node=condition.next;int count=0;
    while(node!=&quest){auto* next=node->next;delete node;node=next;++count;}
    CHECK(count==3);
    for(int kind=0;kind<8;++kind){
        RE::TESConditionItem unsupported;unsupported.data.functionData.params[0]=&vanilla;
        if(kind==0)unsupported.data.flags.isOR=true;
        if(kind==1)unsupported.data.flags.global=true;
        if(kind==2)unsupported.data.flags.usesAliases=true;
        if(kind==3)unsupported.data.flags.usePackData=true;
        if(kind==4)unsupported.data.flags.swapTarget=true;
        if(kind==5)unsupported.data.object=RE::CONDITIONITEMOBJECT::kTarget;
        if(kind==6)unsupported.data.comparisonValue.f=0;
        CHECK(!companion::dialogue::ExtendTradeCondition(&unsupported,kind==7,&vanilla,&managed));
        CHECK(unsupported.next==nullptr);
    }
}
