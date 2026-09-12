#pragma once
#include <algorithm>
#include <cstdint>
#include <span>
#include <vector>
namespace ammo_queue_rules {
using ID=std::uint32_t;
inline constexpr std::size_t limit=64;
inline bool ValidRecord(std::span<const std::uint32_t> words){return words.size()>=2&&words.size()<=limit+2&&words[0]<=1&&words[1]==words.size()-2;}
inline bool Contains(std::span<const ID> order,ID id){return id&&std::find(order.begin(),order.end(),id)!=order.end();}
template<class Available> ID Next(std::span<const ID> order,ID after,Available available){
    auto it=order.begin();if(after){it=std::find(it,order.end(),after);if(it==order.end())return 0;++it;}
    for(;it!=order.end();++it)if(*it&&available(*it))return *it;
    return 0; // one forward pass, no wrap and no out-of-queue selection
}
struct Tracker {
    ID attempted=0;bool waiting=false,finished=false;
    void Reset(){attempted=0;waiting=false;finished=false;}
    void Cancel(){waiting=false;} // failed equip is not retried every poll
    template<class Count> ID Tick(std::span<const ID> order,ID current,Count count){
        const auto head=Next(order,0,[&](ID id){return count(id)>0;});finished=!head;
        if(!head){waiting=false;attempted=0;return 0;}
        if(current==head){waiting=false;attempted=0;return 0;}
        if(waiting||attempted==head)return 0;
        attempted=head;waiting=true;return head;
    }
};
template<class Count> bool Prune(std::vector<ID>& order,Count count){
    const auto before=order.size();std::erase_if(order,[&](ID id){return count(id)<=0;});return order.size()!=before;
}
}
