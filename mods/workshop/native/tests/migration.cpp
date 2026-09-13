#include "legacy_queue.h"
#include "../../../durability-manager/native/src/dismantle_rules.h"
#include <sstream>
#include <stdexcept>
#include <iostream>
#include <fstream>
void require(bool ok){if(!ok)throw std::runtime_error("migration test failed");}
void word(std::string& s,std::uint32_t w){s.append(reinterpret_cast<const char*>(&w),4);}
std::string fixture(){
    std::string s="SKSE";for(auto w:{1U,0U,0U,2U,0x4455524DU,1U,16U,123U,1U,4U,17U,0x4D415151U,1U,28U,0x51554555U,1U,16U,1U,2U,0xFE123800U,0x01001234U})word(s,w);return s;
}
auto parse(const std::string& data){std::istringstream in(data,std::ios::binary);return workshop_migration::ReadLegacyQueue(in);}
int main(int argc, char** argv){
    require(dismantle_rules::MaterialYield(6,1)==3);
    require(dismantle_rules::MaterialYield(6,3)==1);
    require(dismantle_rules::MaterialYield(1,100)==0);
    require(dismantle_rules::MaterialYield(-1,1)==0);
    require(dismantle_rules::MaterialYield(10,0)==0);
    require(dismantle_rules::MaterialYield(INT32_MAX,1)==INT32_MAX/2);
    const auto data=fixture();const auto q=parse(data);
    require(q&&*q==std::vector<std::uint32_t>({1,2,0xFE123800,0x01001234}));
    for(std::size_t i=0;i<data.size();++i)require(!parse(data.substr(0,i)));
    auto bad=data;bad[0]='X';require(!parse(bad));
    bad=data;bad[4]=2;require(!parse(bad));
    bad=data;bad[16]=0;require(!parse(bad));
    bad=data;bad[56]=0;require(!parse(bad)); // invalid plugin payload length
    bad=data;bad[76]=65;require(!parse(bad)); // item count mismatches record
    std::string empty="SKSE";for(auto w:{1U,0U,0U,0U})word(empty,w);require(!parse(empty));
    std::cout<<"Legacy queue parser: identity, unrelated records, all truncations, version and bounds passed.\n";
    if(argc>1){std::ifstream file(argv[1],std::ios::binary);require(bool(file));const auto real=workshop_migration::ReadLegacyQueue(file);std::cout<<"Existing co-save legacy queue: "<<(real?std::to_string(real->size()-2)+" entries":"no supported legacy queue record")<<"\n";}
}
