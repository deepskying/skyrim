#pragma once
#include <memory>

namespace companion::dialogue {
// Extend only an isolated positive self/faction clause. Skip unfamiliar overrides
// rather than regrouping another mod's OR chain or bypassing its voice/quest gates.
inline bool ExtendTradeCondition(RE::TESConditionItem* node, bool previousOr,
                                 RE::TESFaction* vanilla, RE::TESFaction* managed)
{
    if(!node||!vanilla||!managed)return false;
    const auto& d=node->data;
    if(previousOr||d.flags.isOR||d.flags.global||d.flags.usesAliases||d.flags.usePackData||d.flags.swapTarget||
       d.object!=RE::CONDITIONITEMOBJECT::kSelf||
       d.functionData.function!=RE::FUNCTION_DATA::FunctionID::kGetInFaction||
       d.functionData.params[0]!=vanilla||d.flags.opCode!=RE::CONDITION_ITEM_DATA::OpCode::kEqualTo||
       d.comparisonValue.f!=1.0f)return false;

    // V OR (M AND T) = (V OR M) AND (V OR T). The engine groups OR clauses.
    auto member=std::make_unique<RE::TESConditionItem>();
    auto original=std::make_unique<RE::TESConditionItem>();
    auto teammate=std::make_unique<RE::TESConditionItem>();
    member->data=d;
    member->data.functionData.params[0]=managed;
    original->data=d;
    original->data.flags.isOR=true;
    teammate->data=d;
    teammate->data.functionData.function=RE::FUNCTION_DATA::FunctionID::kGetPlayerTeammate;
    teammate->data.functionData.params[0]=nullptr;
    teammate->data.functionData.params[1]=nullptr;
    teammate->next=node->next;
    original->next=teammate.release();
    member->next=original.release();
    node->data.flags.isOR=true;
    node->next=member.release();
    return true;
}
}
