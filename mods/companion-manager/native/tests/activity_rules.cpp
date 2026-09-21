#include "../src/activity_rules.h"
#include "../src/outfit_rules.h"
#ifdef NDEBUG
#undef NDEBUG
#endif
#include <cassert>
#include <limits>
using namespace companion::activity;
int main() {
    namespace outfit = companion::outfit;
    assert(outfit::CanUnlockReplacement(true,true,false,0x80,0x80));
    assert(!outfit::CanUnlockReplacement(false,true,false,0x80,0x80));
    assert(!outfit::CanUnlockReplacement(true,false,false,0x80,0x80));
    assert(!outfit::CanUnlockReplacement(true,true,true,0x80,0x80));
    assert(!outfit::CanUnlockReplacement(true,true,false,0x80,4));
    assert(!outfit::CanUnlockReplacement(true,true,false,0x80,0));
    using companion::outfit::Candidate;
    using companion::outfit::Select;
    // Locked body wins over unlocked alternatives; missing accessory slots use fallback.
    const std::vector<Candidate> wardrobe={{0,1,false,false},{1,1,true,false},{2,2,false,false},{3,4,false,false}};
    assert((Select(wardrobe,4,true)==std::vector<std::size_t>{1,2}));
    assert((Select(wardrobe,0,false)==std::vector<std::size_t>{1}));
    // No locked clothes: manual picks usable, non-overlapping alternatives, including multi-slot clothing.
    assert((Select({{0,3,false,false},{1,2,false,false},{2,4,false,false}},0,true)==std::vector<std::size_t>{0,2}));
    assert(Select({{0,1,false,false}},0,false).empty());
    // Protected slots cannot be replaced, even by locked clothes; zero masks are not equip candidates.
    assert(Select({{0,3,true,false},{1,0,true,false}},1,true).empty());
    // Within the preferred tier, choose a different item when one fits.
    assert((Select({{0,1,true,true},{1,1,true,false},{2,2,false,true}},0,true)==std::vector<std::size_t>{1,2}));
    assert((Select({{0,1,false,true},{1,1,false,false}},0,true)==std::vector<std::size_t>{1}));
    // A locked current outfit must not block an unlocked manual replacement.
    assert((Select({{0,1,true,true},{1,1,false,false}},0,true)==std::vector<std::size_t>{1}));
    assert((Select({{0,1,true,true},{1,1,false,false}},0,false)==std::vector<std::size_t>{0}));
    // Unworn locked alternatives still beat unworn unlocked alternatives.
    assert((Select({{0,1,false,false},{1,1,true,false}},0,true)==std::vector<std::size_t>{1}));
    // Protected multi-slot alternatives cannot defeat protection; an independent part can change.
    assert((Select({{0,3,true,false},{1,4,false,false},{2,1,true,true}},2,true)==std::vector<std::size_t>{1,2}));
    assert(outfit::Confirmation(2,0)==outfit::Result::Unconfirmed);
    assert(outfit::Confirmation(2,1)==outfit::Result::Partial);
    assert(outfit::Confirmation(2,2)==outfit::Result::Changed);
    assert(outfit::Changed(outfit::Result::Partial));
    assert(!outfit::Changed(outfit::Result::Unconfirmed));
    assert(outfit::PollConfirmation(5,0,false)==outfit::Result::Pending);
    assert(outfit::PollConfirmation(5,2,false)==outfit::Result::Pending);
    assert(outfit::PollConfirmation(5,5,false)==outfit::Result::Changed);
    assert(outfit::PollConfirmation(5,2,true)==outfit::Result::Partial);
    assert(outfit::PollConfirmation(5,0,true)==outfit::Result::Unconfirmed);
    assert(!outfit::Changed(outfit::Result::Pending));
    // For any protected mask and two item masks, an eligible unworn alternative is selected.
    for (unsigned protectedMask=0; protectedMask<8; ++protectedMask)
        for (unsigned wornMask=1; wornMask<8; ++wornMask)
            for (unsigned newMask=1; newMask<8; ++newMask) {
                const auto choice=Select({{0,wornMask,true,true},{1,newMask,false,false}},protectedMask,true);
                const bool selected=std::find(choice.begin(),choice.end(),1)!=choice.end();
                assert(selected == !(protectedMask & newMask));
            }
    // Probability boundaries include no saved sets even at 100%.
    for(int roll=0;roll<100;++roll) {
        assert(!outfit::UseSaved(0,100,roll));assert(!outfit::UseSaved(3,0,roll));
        assert(outfit::UseSaved(3,100,roll));assert(outfit::UseSaved(3,70,roll)==(roll<70));
    }
    assert(outfit::EligiblePart(32,(1u<<2)|(1u<<7),0,false,false));
    assert(outfit::EligiblePart(37,(1u<<2)|(1u<<7),0,false,false));
    assert(!outfit::EligiblePart(32,(1u<<2)|(1u<<7),1u<<7,false,false));
    assert(!outfit::EligiblePart(39,1u<<9,0,false,false));
    assert(!outfit::EligiblePart(29,1,0,false,false));
    assert(!outfit::EligiblePart(62,1,0,false,false));
    assert(outfit::EligiblePart(61,0x80000000u,0,false,false));
    assert(!outfit::EligiblePart(32,4,0,true,false));
    assert(!outfit::EligiblePart(32,4,0,false,true));
    auto prefs=Defaults(); assert(Valid(prefs));
    for(auto k:{"radius","categories","outfitHours"}) {auto bad=prefs;bad[k]=-1;assert(!Valid(bad));}
    auto bad=prefs;bad["loot"]=1;assert(!Valid(bad));bad=prefs;bad["radius"]=4.5;assert(!Valid(bad));
    assert(Fits(300,290,6,5)==1); assert(Fits(300,300,1,5)==0);
    assert(Fits(300,301,0,100)==0);assert(Fits(300,300,0,100)==100);
    assert(Fits(300,299.95f,.1f,10)==0); assert(Fits(300,200,0,50000)==50000);
    assert(Fits(300,200,std::numeric_limits<float>::quiet_NaN(),1)==0);
    assert(!Worth(1,19,1,prefs));assert(!Worth(1,100,21,prefs));assert(Worth(1,100,20,prefs));
    assert(Worth(8,1,1,prefs));prefs["categories"]=1;assert(!Worth(8,100,0,prefs));
    assert(SaleCount(5,40,100)==2);assert(SaleCount(5,40,39)==0);assert(SaleCount(5,0,100)==0);
    assert(CanRun(true,false,false,false,true));
    assert(!CanRun(true,true,false,false,true));assert(!CanRun(false,false,false,false,true));
    assert(!CanRun(true,false,true,false,true));assert(!CanRun(true,false,false,true,true));assert(!CanRun(true,false,false,false,false));
}
