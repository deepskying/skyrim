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
    ID watched=0;int previous=0;bool waiting=false,finished=false;
    void Reset(){watched=0;previous=0;waiting=false;finished=false;}
    void Observe(ID id,int count,std::span<const ID> order){watched=Contains(order,id)&&count>0?id:0;previous=watched?count:0;}
    template<class Count> ID Tick(std::span<const ID> order,ID current,Count count){
        if(waiting||finished)return 0;
        if(watched&&previous>0&&count(watched)==0){
            const auto next=Next(order,watched,[&](ID id){return count(id)>0;});
            watched=0;previous=0;waiting=next!=0;finished=!next;return next;
        }
        // A manual selection is respected while the previous stack still exists.
        if(current!=watched)finished=false;
        if(!finished)Observe(current,count(current),order);
        return 0;
    }
};
}
