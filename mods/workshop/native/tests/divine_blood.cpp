#ifdef NDEBUG
#undef NDEBUG
#endif
#include "../../../divine-blood/native/src/rules.h"
#include <cassert>
#include <climits>
using namespace divine_blood_rules;
int main(){
    assert(Cost(10,0)==10&&Cost(10,9)==10&&Cost(10,10)==11&&Cost(10,20)==12);
    assert(Cost(3,10)==4&&Cost(INT_MAX,UINT32_MAX)==INT_MAX);
    assert(Output(19,20,20,10,10)==1); // All 19 points are offered; surplus is discarded.
    assert(Output(20,20,9,10,10)==0&&Output(9,20,20,10,10)==0);
    assert(Output(21,20,20,10,10)==0); // Never silently clamp an overfilled selection.
    assert(Output(20,20,11,10,10)==1&&Output(20,20,20,10,10)==2);
    assert(Output(20,20,20,11,11)==1);
    assert(Output(INT64_MAX,INT_MAX,INT_MAX,1,1)==0);
    for(int cap=1;cap<=100;++cap)for(int a=0;a<=cap;++a)for(int s=0;s<=100;++s){
        const int n=Output(a,cap,s,7,11);assert(n*7<=a&&n*11<=s);
        assert((n+1)*7>a||(n+1)*11>s); // Maximum, not an arbitrary/manual quantity.
    }
}
