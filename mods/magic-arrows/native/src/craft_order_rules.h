#pragma once
// Pure rules for the queued magic arrow crafting order. No game types here so the
// limits, merging, progress, refund arithmetic and HUD labels stay offline testable.
#include "crafting_plan.h"
#include <cstdio>
#include <string>
#include <vector>
namespace craft_order_rules {
inline constexpr int perSpellLimit=10000;          // queued arrows of one spell
inline constexpr int materialLimit=28;             // locked stacks kept for the refund
struct Entry {
    // One entry per spell: batches of the same spell merge, different spells queue.
    std::uint32_t spell=0,arrow=0;
    int family=11;                                  // arrow family index, drives the diamond colour
    int total=0,remaining=0;                        // accepted and still to craft
    int manaPerArrow=0,chargePerArrow=0,goldPerArrow=0;
    std::vector<crafting::Stack> bases,materials;   // locked at order time, used for the refund
};
inline int Find(const std::vector<Entry>& entries,std::uint32_t spell) {
    for (std::size_t i=0;i<entries.size();++i) if (entries[i].spell==spell) return static_cast<int>(i);
    return -1;
}
inline int Queued(const std::vector<Entry>& entries,std::uint32_t spell) {
    const int index=Find(entries,spell);
    return index<0?0:entries[static_cast<std::size_t>(index)].remaining;
}
// The start button stays disabled until the requested batch still fits the queue ceiling.
inline bool Accept(const std::vector<Entry>& entries,std::uint32_t spell,int count) {
    return count>0&&Queued(entries,spell)+count<=perSpellLimit;
}
// Same spell: merge in place so the spell keeps its queue position. New spell: append.
inline void Add(std::vector<Entry>& entries,Entry batch) {
    const int index=Find(entries,batch.spell);
    if (index<0) { entries.push_back(std::move(batch)); return; }
    auto& target=entries[static_cast<std::size_t>(index)];
    target.total+=batch.total;target.remaining+=batch.remaining;
    for (const auto& s:batch.bases) {
        auto it=std::find_if(target.bases.begin(),target.bases.end(),[&](const crafting::Stack& x){return x.id==s.id;});
        if (it==target.bases.end()) target.bases.push_back(s); else it->count+=s.count;
    }
    for (const auto& s:batch.materials) {
        auto it=std::find_if(target.materials.begin(),target.materials.end(),[&](const crafting::Stack& x){return x.id==s.id;});
        if (it==target.materials.end()) target.materials.push_back(s); else it->count+=s.count;
    }
}
// One arrow per tick. Returns false once the entry is finished.
inline bool Advance(Entry& entry) {
    if (entry.remaining<=0) return false;
    --entry.remaining;
    return entry.remaining>0;
}
// Square brackets [0,1] of the arrows still to craft, for the diamond border.
inline double Progress(const Entry& entry) {
    return entry.total>0?static_cast<double>(entry.remaining)/entry.total:0.0;
}
// Bases are consumed in selection order, so the refund returns the tail of each stack.
inline std::vector<crafting::Stack> RefundBases(const Entry& entry) {
    const int consumed=entry.total-entry.remaining;
    std::vector<crafting::Stack> refund;
    int left=consumed;
    for (std::size_t i=entry.bases.size();i>0&&left>0;--i) {
        const auto& stack=entry.bases[i-1];
        const int take=std::min(stack.count,left);
        if (take>0) refund.push_back({stack.id,take,0});
        left-=take;
    }
    return refund;
}
// Charge is spent per arrow from the front of the locked basket. Whole items are spent,
// exactly like the crafting plan, so a partly used stack still returns its unused items.
inline std::vector<crafting::Stack> RefundMaterials(const Entry& entry) {
    std::int64_t left=static_cast<std::int64_t>(entry.total-entry.remaining)*entry.chargePerArrow;
    std::vector<crafting::Stack> refund;
    for (const auto& stack:entry.materials) {
        if (stack.count<=0) continue;
        if (left<=0) { refund.push_back({stack.id,stack.count,stack.units}); continue; }
        const std::int64_t capacity=static_cast<std::int64_t>(stack.count)*stack.units;
        if (left>=capacity) { left-=capacity; continue; }
        const int used=static_cast<int>((left+stack.units-1)/stack.units);
        const int returned=stack.count-used;
        if (returned>0) refund.push_back({stack.id,returned,stack.units});
        left=0;
    }
    return refund;
}
inline int RefundGold(const Entry& entry) { return entry.remaining*entry.goldPerArrow; }
// HUD label: exact below 1000, one decimal K above it, whole thousands without the decimal.
inline std::string CountLabel(int count) {
    if (count<0) count=0;
    if (count<1000) return std::to_string(count);
    const double thousands=count/1000.0;
    const int whole=static_cast<int>(thousands);
    char buffer[16]{};
    if (std::abs(thousands-whole)<0.05) std::snprintf(buffer,sizeof(buffer),"%dK",whole);
    else std::snprintf(buffer,sizeof(buffer),"%.1fK",thousands);
    return buffer;
}
// Pause reasons in priority order; an empty result means the queue may advance.
enum class Pause { none, panel, loading, dead, combat };
inline const char* Reason(Pause pause) {
    switch (pause) {
    case Pause::panel: return "工坊打开中";
    case Pause::loading: return "载入中";
    case Pause::dead: return "等待复活";
    case Pause::combat: return "战斗中暂停";
    default: return "";
    }
}
inline Pause Evaluate(bool panelOpen,bool loading,bool dead,bool combat,bool pauseInCombat) {
    if (loading) return Pause::loading;
    if (dead) return Pause::dead;
    if (panelOpen) return Pause::panel;
    if (combat&&pauseInCombat) return Pause::combat;
    return Pause::none;
}
// Co-save encoding. One record holds every queued spell; the loader supplies the form ID
// resolver so this stays independent of the game.
inline constexpr std::uint32_t recordVersion=1;
inline constexpr int baseKindMax=32,materialKindMax=128;
inline void Push(std::vector<std::uint32_t>& words,const crafting::Stack& stack) {
    words.push_back(stack.id);words.push_back(static_cast<std::uint32_t>(stack.count));words.push_back(static_cast<std::uint32_t>(stack.units));
}
inline bool Read(const std::vector<std::uint32_t>& words,std::size_t& at,crafting::Stack& stack) {
    if (at+3>words.size()) return false;
    stack={words[at],static_cast<int>(words[at+1]),static_cast<int>(words[at+2])};at+=3;return true;
}
inline std::vector<std::uint32_t> Encode(const std::vector<Entry>& entries) {
    std::vector<std::uint32_t> words{recordVersion,static_cast<std::uint32_t>(entries.size())};
    for (const auto& entry:entries) {
        words.push_back(entry.spell);words.push_back(entry.arrow);words.push_back(static_cast<std::uint32_t>(entry.family));
        words.push_back(static_cast<std::uint32_t>(entry.total));words.push_back(static_cast<std::uint32_t>(entry.remaining));
        words.push_back(static_cast<std::uint32_t>(entry.manaPerArrow));words.push_back(static_cast<std::uint32_t>(entry.chargePerArrow));
        words.push_back(static_cast<std::uint32_t>(entry.goldPerArrow));
        words.push_back(static_cast<std::uint32_t>(entry.bases.size()));
        for (const auto& stack:entry.bases) Push(words,stack);
        words.push_back(static_cast<std::uint32_t>(entry.materials.size()));
        for (const auto& stack:entry.materials) Push(words,stack);
    }
    return words;
}
// Resolve maps a saved ID onto this load order; a spell or arrow that no longer resolves
// drops its entry so the caller can refund the locked resources.
template <class Resolve>
bool Decode(const std::vector<std::uint32_t>& words,std::vector<Entry>& out,Resolve resolve) {
    out.clear();
    if (words.size()<2||words[0]!=recordVersion) return false;
    const std::uint32_t count=words[1];
    if (count>static_cast<std::uint32_t>(baseKindMax*materialKindMax)) return false;
    std::size_t at=2;
    for (std::uint32_t i=0;i<count;++i) {
        if (at+9>words.size()) return false;
        Entry entry;
        entry.spell=words[at];entry.arrow=words[at+1];entry.family=static_cast<int>(words[at+2]);
        entry.total=static_cast<int>(words[at+3]);entry.remaining=static_cast<int>(words[at+4]);
        entry.manaPerArrow=static_cast<int>(words[at+5]);entry.chargePerArrow=static_cast<int>(words[at+6]);
        entry.goldPerArrow=static_cast<int>(words[at+7]);
        const std::uint32_t bases=words[at+8];at+=9;
        if (bases>static_cast<std::uint32_t>(baseKindMax)) return false;
        for (std::uint32_t b=0;b<bases;++b) { crafting::Stack stack; if (!Read(words,at,stack)) return false; entry.bases.push_back(stack); }
        if (at>=words.size()) return false;
        const std::uint32_t materials=words[at++];
        if (materials>static_cast<std::uint32_t>(materialKindMax)) return false;
        for (std::uint32_t m=0;m<materials;++m) { crafting::Stack stack; if (!Read(words,at,stack)) return false; entry.materials.push_back(stack); }
        // Reject records that cannot describe a queued batch instead of trusting them.
        if (entry.total<=0||entry.remaining<0||entry.remaining>entry.total||entry.remaining>perSpellLimit||
            entry.manaPerArrow<0||entry.chargePerArrow<0||entry.goldPerArrow<0) return false;
        std::uint32_t spell=0,arrow=0;
        if (!resolve(entry.spell,spell)||!spell||!resolve(entry.arrow,arrow)||!arrow) continue;
        entry.spell=spell;entry.arrow=arrow;
        out.push_back(std::move(entry));
    }
    return at==words.size();
}
}
