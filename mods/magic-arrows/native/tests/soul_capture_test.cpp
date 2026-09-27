#include "soul_capture_rules.h"
#include <iostream>
#include <stdexcept>
using namespace soul_capture_rules;
void check(bool ok){if(!ok)throw std::runtime_error("soul capture regression");}
int main(){
    check(Candidates(1)==std::vector<std::uint32_t>({0x2E4E2,0x2E500}));
    check(Candidates(3)==std::vector<std::uint32_t>({0x2E4E6,0x2E500})); // bandit-sized soul, black gem as the fallback
    check(Candidates(5)==std::vector<std::uint32_t>({0x2E4FC,0x2E500}));
    check(Candidates(0)==std::vector<std::uint32_t>({0x2E500}));         // unknown soul level still tries the black gem
    for(std::size_t i=1;i<emptyGems.size();++i)check(emptyGems[i-1]<emptyGems[i]);

    std::vector<Entry> list;
    check(capacity==128&&windowMilliseconds==300000);      // marks survive a five minute fight
    Arm(list,0x100,0x14,1000,7);
    check(Armed(list,0x100,1000,7));
    check(!Armed(list,0x101,1000,7));
    check(!Armed(list,0x100,1000+windowMilliseconds+1,7)); // the arrow's window is over
    check(!Armed(list,0x100,1000,8));                      // loading a save drops the pending capture
    Arm(list,0x100,0x14,1000+windowMilliseconds-1,7);
    check(list.size()==1);                                 // re-arming refreshes instead of duplicating
    for(std::uint32_t i=0;i<capacity+5;++i)Arm(list,0x1000+i,0x14,2000,7);
    check(list.size()==capacity);
    check(Armed(list,0x1000+capacity+4,2000,7));
    check(!Armed(list,0x1000,2000,7));                     // the oldest entry leaves first
    std::cout<<"PASS: soul gem candidates, arm window, save epoch, refresh and capacity pruning\n";
}
