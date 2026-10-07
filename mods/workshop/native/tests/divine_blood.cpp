#ifdef NDEBUG
#undef NDEBUG
#endif
#include "../../../divine-blood/native/src/rules.h"
#include <cassert>
#include <climits>
using namespace divine_blood_rules;
int main(){
    assert(IngredientPoints(2,0)==2&&IngredientPoints(5,0)==5);
    assert(IngredientPoints(.6f,0)==1&&IngredientPoints(1.25f,0)==2);
    assert(IngredientPoints(5,30)==5&&IngredientPoints(5,120)==10);
    assert(IngredientPoints(5,UINT32_MAX)==10);
    assert(IngredientPoints(2,0,3)==6);
    assert(IngredientPoints(0,0)==0&&IngredientPoints(-1,30)==0);
    assert(IngredientPoints(0,0,1,true)==1);
    assert(IngredientPoints(std::numeric_limits<float>::quiet_NaN(),0)==0);
    assert(IngredientPoints(std::numeric_limits<float>::infinity(),0)==0);
    assert(IngredientPoints(std::numeric_limits<float>::max(),120,1000000)==1000000);
    assert(Output(2*IngredientPoints(5,0),20,20,10,10)==1);

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
