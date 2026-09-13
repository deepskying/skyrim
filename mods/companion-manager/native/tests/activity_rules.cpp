#include "../src/activity_rules.h"
#ifdef NDEBUG
#undef NDEBUG
#endif
#include <cassert>
#include <limits>
using namespace companion::activity;
int main() {
    auto prefs=Defaults(); assert(Valid(prefs));
    for(auto k:{"radius","categories","outfitHours"}) {auto bad=prefs;bad[k]=-1;assert(!Valid(bad));}
    auto bad=prefs;bad["loot"]=1;assert(!Valid(bad));bad=prefs;bad["radius"]=4.5;assert(!Valid(bad));
    assert(Fits(300,290,6,5)==1); assert(Fits(300,300,1,5)==0);
    assert(Fits(300,301,0,100)==0);assert(Fits(300,300,0,100)==100);
    assert(Fits(300,299.95f,.1f,10)==0); assert(Fits(300,200,0,50000)==50000);
    assert(Fits(300,200,std::numeric_limits<float>::quiet_NaN(),1)==0);
    assert(!Worth(1,19,1,prefs));assert(!Worth(1,100,21,prefs));assert(Worth(1,100,20,prefs));
    assert(Worth(8,1,1,prefs));prefs["categories"]=1;assert(!Worth(8,100,0,prefs));
    assert(SaleCount(5,40,100)==2);assert(SaleCount(5,40,39)==0);assert(SaleCount(5,0,100)==0);
    assert(CanRun(true,false,false,false,true));
    assert(!CanRun(true,true,false,false,true));assert(!CanRun(false,false,false,false,true));
    assert(!CanRun(true,false,true,false,true));assert(!CanRun(true,false,false,true,true));assert(!CanRun(true,false,false,false,false));
}
