#include "normal_plan.h"
#include <iostream>
using namespace normal_crafting;
void check(bool b){if(!b)throw std::runtime_error("assertion failed");}
template<class F>void reject(F f){bool rejected=false;try{f();}catch(const std::runtime_error&){rejected=true;}check(rejected);}
int main(){
    std::vector<Stack> recipe{{1,1,0},{2,1,0}},stock{{1,4,0},{2,8,0}};
    auto p=MakePlan(3,24,recipe,stock);check(p.total==72&&p.ingredients[0].count==3&&p.ingredients[1].count==3);
    auto duplicate=MakePlan(2,24,{{1,1,0},{1,1,0}},stock);check(duplicate.ingredients.size()==1&&duplicate.ingredients[0].count==4);
    reject([&]{MakePlan(3,24,{{1,1,0},{1,1,0}},stock);});
    reject([&]{MakePlan(5,24,recipe,stock);});
    reject([&]{MakePlan(0,24,recipe,stock);});
    reject([&]{MakePlan(-1,24,recipe,stock);});
    reject([&]{MakePlan(101,1,recipe,stock);});
    reject([&]{MakePlan(100,24,recipe,stock);});
    reject([&]{MakePlan(1,0,recipe,stock);});
    reject([&]{MakePlan(1,24,{},stock);});
    reject([&]{MakePlan(1,24,{{1,0,0}},stock);});
    reject([&]{MakePlan(1,24,{{3,1,0}},stock);});
    reject([&]{MakePlan(100,1,{{1,2147483647,0}},{{1,2147483647,0}});});
    check(MakePlan(100,10,recipe,{{1,100,0},{2,100,0}}).total==1000);
    std::cout<<"Normal planner: batch yield, merged requirements, shortage, limits and overflow passed.\n";
}
