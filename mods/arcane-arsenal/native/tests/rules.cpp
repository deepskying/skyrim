#include "rules.h"
#include <cstdlib>
#include <iostream>
void check(bool v){if(!v)std::abort();}
int main(){
    rules::Marks m;
    check(!m.hit(1,2,0));check(!m.hit(1,2,1));check(m.hit(1,2,2));check(m.marks.empty());
    check(!m.hit(1,2,3));check(!m.hit(1,2,7));check(m.marks.at({1,2}).stacks==1);
    check(!m.hit(2,2,7));check(!m.hit(1,3,7));check(m.marks.at({2,2}).stacks==1);
    for(int i=10;i<50;++i)m.hit(1,i,8.f+(i-10)*.01f);
    int n=0;for(auto& [k,v]:m.marks)if(k.first==1)++n;check(n==16);
    check(!rules::canStart(1,1,0));check(!rules::canStart(1,0,1));check(rules::canStart(3,1,0));check(!rules::canStart(3,1,1));
    check(rules::advance(1,.7f,true)==1);check(rules::advance(.2f,.7f,false)==0);
    // A fast projectile crossing the entire actor in one frame still intersects.
    check(rules::segmentParameter(50,0,0,0,0,0,100,0,0)==.5f);
    check(rules::segmentParameter(-20,0,0,0,0,0,100,0,0)==0);
    check(rules::segmentParameter(200,0,0,0,0,0,100,0,0)==1);
    std::cout<<"staff rules passed\n";
}
