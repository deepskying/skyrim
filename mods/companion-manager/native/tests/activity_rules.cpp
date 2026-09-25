#include "../src/activity_rules.h"
#include "../src/outfit_rules.h"
#ifdef NDEBUG
#undef NDEBUG
#endif
#include "check.h"
#include <limits>
using namespace companion::activity;
int main() {
    namespace outfit = companion::outfit;
    CHECK(outfit::CanUnlockReplacement(true,true,false,0x80,0x80));
    CHECK(!outfit::CanUnlockReplacement(false,true,false,0x80,0x80));
    CHECK(!outfit::CanUnlockReplacement(true,false,false,0x80,0x80));
    CHECK(!outfit::CanUnlockReplacement(true,true,true,0x80,0x80));
    CHECK(!outfit::CanUnlockReplacement(true,true,false,0x80,4));
    CHECK(!outfit::CanUnlockReplacement(true,true,false,0x80,0));
    using companion::outfit::Candidate;
    using companion::outfit::Select;
    // Locked body wins over unlocked alternatives; missing accessory slots use fallback.
    const std::vector<Candidate> wardrobe={{0,1,false,false},{1,1,true,false},{2,2,false,false},{3,4,false,false}};
    CHECK((Select(wardrobe,4,true)==std::vector<std::size_t>{1,2}));
    CHECK((Select(wardrobe,0,false)==std::vector<std::size_t>{1}));
    // No locked clothes: manual picks usable, non-overlapping alternatives, including multi-slot clothing.
    CHECK((Select({{0,3,false,false},{1,2,false,false},{2,4,false,false}},0,true)==std::vector<std::size_t>{0,2}));
    CHECK(Select({{0,1,false,false}},0,false).empty());
    // Protected slots cannot be replaced, even by locked clothes; zero masks are not equip candidates.
    CHECK(Select({{0,3,true,false},{1,0,true,false}},1,true).empty());
    // Within the preferred tier, choose a different item when one fits.
    CHECK((Select({{0,1,true,true},{1,1,true,false},{2,2,false,true}},0,true)==std::vector<std::size_t>{1,2}));
    CHECK((Select({{0,1,false,true},{1,1,false,false}},0,true)==std::vector<std::size_t>{1}));
    // A locked current outfit must not block an unlocked manual replacement.
    CHECK((Select({{0,1,true,true},{1,1,false,false}},0,true)==std::vector<std::size_t>{1}));
    CHECK((Select({{0,1,true,true},{1,1,false,false}},0,false)==std::vector<std::size_t>{0}));
    // Unworn locked alternatives still beat unworn unlocked alternatives.
    CHECK((Select({{0,1,false,false},{1,1,true,false}},0,true)==std::vector<std::size_t>{1}));
    // Protected multi-slot alternatives cannot defeat protection; an independent part can change.
    CHECK((Select({{0,3,true,false},{1,4,false,false},{2,1,true,true}},2,true)==std::vector<std::size_t>{1,2}));
    CHECK(outfit::Confirmation(2,0)==outfit::Result::Unconfirmed);
    CHECK(outfit::Confirmation(2,1)==outfit::Result::Partial);
    CHECK(outfit::Confirmation(2,2)==outfit::Result::Changed);
    CHECK(outfit::Changed(outfit::Result::Partial));
    CHECK(!outfit::Changed(outfit::Result::Unconfirmed));
    CHECK(outfit::PollConfirmation(5,0,false)==outfit::Result::Pending);
    CHECK(outfit::PollConfirmation(5,2,false)==outfit::Result::Pending);
    CHECK(outfit::PollConfirmation(5,5,false)==outfit::Result::Changed);
    CHECK(outfit::PollConfirmation(5,2,true)==outfit::Result::Partial);
    CHECK(outfit::PollConfirmation(5,0,true)==outfit::Result::Unconfirmed);
    CHECK(!outfit::Changed(outfit::Result::Pending));
    // For any protected mask and two item masks, an eligible unworn alternative is selected.
    for (unsigned protectedMask=0; protectedMask<8; ++protectedMask)
        for (unsigned wornMask=1; wornMask<8; ++wornMask)
            for (unsigned newMask=1; newMask<8; ++newMask) {
                const auto choice=Select({{0,wornMask,true,true},{1,newMask,false,false}},protectedMask,true);
                const bool selected=std::find(choice.begin(),choice.end(),1)!=choice.end();
                CHECK(selected == !(protectedMask & newMask));
            }
    // Probability boundaries include no saved sets even at 100%.
    for(int roll=0;roll<100;++roll) {
        CHECK(!outfit::UseSaved(0,100,roll));CHECK(!outfit::UseSaved(3,0,roll));
        CHECK(outfit::UseSaved(3,100,roll));CHECK(outfit::UseSaved(3,70,roll)==(roll<70));
    }
    CHECK(outfit::EligiblePart(32,(1u<<2)|(1u<<7),0,false,false));
    CHECK(outfit::EligiblePart(37,(1u<<2)|(1u<<7),0,false,false));
    CHECK(!outfit::EligiblePart(32,(1u<<2)|(1u<<7),1u<<7,false,false));
    CHECK(!outfit::EligiblePart(39,1u<<9,0,false,false));
    CHECK(!outfit::EligiblePart(29,1,0,false,false));
    CHECK(!outfit::EligiblePart(62,1,0,false,false));
    CHECK(outfit::EligiblePart(61,0x80000000u,0,false,false));
    CHECK(!outfit::EligiblePart(32,4,0,true,false));
    CHECK(!outfit::EligiblePart(32,4,0,false,true));
    auto prefs=Defaults(); CHECK(Valid(prefs));
    for(auto k:{"radius","categories","outfitHours"}) {auto bad=prefs;bad[k]=-1;CHECK(!Valid(bad));}
    auto bad=prefs;bad["loot"]=1;CHECK(!Valid(bad));bad=prefs;bad["radius"]=4.5;CHECK(!Valid(bad));
    CHECK(Fits(300,290,6,5)==1); CHECK(Fits(300,300,1,5)==0);
    CHECK(Fits(300,301,0,100)==0);CHECK(Fits(300,300,0,100)==100);
    CHECK(Fits(300,299.95f,.1f,10)==0); CHECK(Fits(300,200,0,50000)==50000);
    CHECK(Fits(300,200,std::numeric_limits<float>::quiet_NaN(),1)==0);
    CHECK(!Worth(1,19,1,prefs));CHECK(!Worth(1,100,21,prefs));CHECK(Worth(1,100,20,prefs));
    CHECK(Worth(8,1,1,prefs));prefs["categories"]=1;CHECK(!Worth(8,100,0,prefs));
    CHECK(SaleCount(5,40,100)==2);CHECK(SaleCount(5,40,39)==0);CHECK(SaleCount(5,0,100)==0);
    CHECK(CanRun(true,false,false,false,true));
    CHECK(!CanRun(true,true,false,false,true));CHECK(!CanRun(false,false,false,false,true));
    CHECK(!CanRun(true,false,true,false,true));CHECK(!CanRun(true,false,false,true,true));CHECK(!CanRun(true,false,false,false,false));
}
