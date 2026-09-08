#include "music_settings.h"
#include "music_rules.h"
#include <iostream>
#include <cstdlib>
void check(bool yes,const char* name){if(!yes){std::cerr<<name<<'\n';std::exit(1);}}
template<class F> void rejects(F fn){bool rejected=false;try{fn();}catch(const std::exception&){rejected=true;}check(rejected,"invalid settings accepted");}
int main(){
    using music::Hotkey; using music::PlaybackSettings;
    auto defaults=PlaybackSettings::parse(nlohmann::json::object());
    check(defaults.fadeSeconds==1.2&&defaults.pauseWithGame,"legacy defaults");
    auto j=defaults.json();j["fadeSeconds"]=-1;rejects([&]{PlaybackSettings::parse(j);});
    j=defaults.json();j["dayStart"]=20;j["dayEnd"]=6;rejects([&]{PlaybackSettings::parse(j);});
    j=defaults.json();j["pauseWithGame"]="true";rejects([&]{PlaybackSettings::parse(j);});
    j=defaults.json();j["combatFadeSeconds"]=100;rejects([&]{PlaybackSettings::parse(j);});
    music::Environment env;env.hour=7;
    check(music::classify(env,8,18)=="explore_night","custom dawn ignored");
    env.hour=18;check(music::classify(env,8,18)=="explore_night","custom dusk boundary");
    check(music::classify(env,0,24)=="explore_day","full day");
    music::SceneGate gate;gate.update("town",0);
    check(gate.update("dungeon",1,0,0)=="dungeon","zero scene wait");
    gate.update("combat",2);check(gate.update("town",3,0,5)=="combat","custom exit wait");
    check(gate.update("town",8,0,5)=="town","custom exit finish");
    Hotkey h;check(h.label()=="Shift + M","default shortcut");
    auto k=h.json();k["scanCode"]=0x40;k["shift"]=false;k["ctrl"]=true;k["alt"]=true;
    auto custom=Hotkey::parse(k);check(custom.label()=="Ctrl + Alt + F6","shortcut label");
    check(custom.matches(0x40,false,true,true),"shortcut match");
    check(!custom.matches(0x40,true,true,true)&&!custom.matches(0x32,false,true,true),"extra modifier or wrong key");
    check(Hotkey::parse(custom.json()).label()==custom.label(),"shortcut JSON roundtrip");
    for(unsigned invalid:{0u,1u,0x2au,0x1du,0x38u,999u}){k["scanCode"]=invalid;rejects([&]{Hotkey::parse(k);});}
    std::cout<<"Playback settings, boundaries, hotkey mapping and validation passed\n";
}
