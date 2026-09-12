#pragma once
#include <cstdint>
#include <string_view>
namespace script_compatibility {
// Audited Mysticism MAG_FrostSlow_Script adds its slow spell to the target on
// effect start and removes it on finish; it does not use actor hand casting.
inline bool FrostSlow(std::uint32_t effectID,std::string_view winningFile,bool sustained,bool aimed,bool hasProjectile){
    return effectID==0xB729D&&winningFile=="mysticismmagic.esp"&&sustained&&aimed&&!hasProjectile;
}
}
