#include "../src/state_rules.h"
#include <cassert>
#include <limits>
using namespace companion::rules;
int main() {
    assert(!ForeignPackagesBlockRecruitment(true, true));
    assert(!ForeignPackagesBlockRecruitment(true, false));
    assert(ForeignPackagesBlockRecruitment(false, true));
    assert(!ForeignPackagesBlockRecruitment(false, false));
    json prefs={{"opacity",82},{"font",15},{"distance",1},{"sandbox",true},{"notifications",true}};
    ValidateSettings(prefs);
    assert(!ValidSetting("font",15.5));assert(!ValidSetting("opacity",97));assert(!ValidSetting("sandbox",1));assert(!ValidSetting("unknown",true));
    assert(Mode(false,false,true,false,1)==0);assert(Mode(false,true,true,true,1)==5);
    assert(Mode(true,true,false,true,2)==3);assert(Mode(true,true,true,false,0)==4);
    for(int d=0;d<3;++d){assert(Mode(true,false,false,false,d)==1+d*10);assert(Mode(true,false,true,false,d)==2+d*10);}
    json member={{"slot",0},{"actor",0xA2C94},{"base",0xA2C8E},{"active",true},{"waiting",false},{"sandbox",true},{"leash",true},{"passive",false},{"raised",false},{"protection",true},{"originalEssential",false},{"originalWaiting",0},{"aggression",1},{"confidence",3},{"originalMax",50},{"home",""},{"learned",json::array()},{"disabled",json::array({0x12FCC})},{"outfit",json::array()}};
    ValidateMember(member);
    auto rejects=[&](const char* key,json value){auto bad=member;bad[key]=value;bool threw=false;try{ValidateMember(bad);}catch(const std::exception&){threw=true;}assert(threw);};
    rejects("slot",32);rejects("slot",1.5);rejects("actor",-1);rejects("base",0);rejects("raised",1);rejects("originalMax",65536);
    rejects("disabled",json::array({-1}));rejects("outfit",json::array({0x100000000ULL}));rejects("home",std::string(4097,'x'));rejects("confidence",std::numeric_limits<double>::infinity());
}
