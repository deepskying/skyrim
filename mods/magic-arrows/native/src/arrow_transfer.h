#pragma once
#include "arrow_identity.h"
#include <algorithm>
namespace arrow_identity {
// Inventory calls can be intercepted. Measure actual changes and restore any
// removed units that were not delivered; do not trust the requested quantities.
template<class SourceCount,class TargetCount,class Remove,class Add,class Restore>
int Transfer(SourceCount sourceCount,TargetCount targetCount,Remove remove,Add add,Restore restore){
    const int source=sourceCount(),target=targetCount();
    if(!Fits(target,source))return 0;
    remove(source);
    const int removed=std::clamp(source-sourceCount(),0,source);
    if(removed!=source){if(removed)restore(removed);return 0;}
    try{add(removed);}
    catch(...){const int delivered=std::clamp(targetCount()-target,0,removed);if(delivered<removed)restore(removed-delivered);throw;}
    const int delivered=std::clamp(targetCount()-target,0,removed);
    if(delivered<removed)restore(removed-delivered);
    return delivered;
}
}
