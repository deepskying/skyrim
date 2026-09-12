#include "script_compatibility.h"
#include <stdexcept>
#include <iostream>
int main(){
    using script_compatibility::FrostSlow;
    auto check=[](bool b){if(!b)throw std::runtime_error("script compatibility boundary failed");};
    // Live 0.9.0 log: Frostbite 2B96B rejected for script effect B729D,
    // concentration, aimed, no projectile. Local Mysticism VMAD/PSC audited.
    check(FrostSlow(0xB729D,"mysticismmagic.esp",true,true,false));
    check(!FrostSlow(0xB729D,"unrelated.esp",true,true,false));
    check(!FrostSlow(0x123456,"mysticismmagic.esp",true,true,false));
    check(!FrostSlow(0xB729D,"mysticismmagic.esp",false,true,false));
    check(!FrostSlow(0xB729D,"mysticismmagic.esp",true,false,false));
    check(!FrostSlow(0xB729D,"mysticismmagic.esp",true,true,true));
    std::cout<<"Mysticism frost slow: live effect descriptor allowed; unknown overrides, other scripts, instant/self/projectile scripts rejected.\n";
}
