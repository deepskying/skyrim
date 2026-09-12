#include "ammo_queue_rules.h"
#include <array>
#include <unordered_map>
#include <stdexcept>
#include <iostream>
using namespace ammo_queue_rules;
void check(bool b){if(!b)throw std::runtime_error("queue regression");}
int main(){
    std::vector<ID> order{10,20,30,40};std::unordered_map<ID,int> stock{{10,2},{20,0},{30,4},{40,1}};
    auto count=[&](ID id){return stock[id];};Tracker t;
    check(Next(order,0,[&](ID id){return count(id)>0;})==10);
    check(Prune(order,count));check((order==std::vector<ID>{10,30,40}));check(!Prune(order,count));
    // Drawing a bow with no ammo, or with the engine's arbitrary choice, starts at head.
    check(t.Tick(order,0,count)==10);check(t.Tick(order,99,count)==0);
    check(t.Tick(order,10,count)==0); // confirmation: do not re-equip current head
    check(t.Tick(order,40,count)==10); // even another queued arrow cannot bypass the head
    t.Cancel();check(t.Tick(order,99,count)==0); // failed submission cannot spin
    t.Reset();check(t.Tick(order,99,count)==10); // bow re-entry / edit re-arms priority
    stock[10]=0;check(Prune(order,count));t.Reset();
    check((order==std::vector<ID>{30,40}));check(t.Tick(order,99,count)==30);
    stock[30]=0;check(Prune(order,count));t.Reset();check(t.Tick(order,10,count)==40);
    stock[40]=0;check(Prune(order,count));t.Reset();check(order.empty());
    check(t.Tick(order,99,count)==0&&t.finished);
    stock[10]=10;check(t.Tick(order,10,count)==0);check(order.empty()); // removed entries do not return on refill
    order={40,10,30};stock[40]=2;stock[30]=3;t.Reset();check(t.Tick(order,30,count)==40);
    order={30,10,40};t.Reset();check(t.Tick(order,40,count)==30); // reorder immediately changes preferred head
    stock[10]=0;stock[30]=0;stock[40]=0;check(Prune(order,count)&&order.empty()); // non-head and multiple depleted entries
    check(Next(order,99,[&](ID){return true;})==0);
    check(Next(std::span<const ID>{},0,[&](ID){return true;})==0);
    check(ValidRecord(std::array<ID,4>{1,2,10,30}));
    check(ValidRecord(std::array<ID,2>{0,0}));
    check(!ValidRecord(std::array<ID,4>{1,3,10,30}));
    check(!ValidRecord(std::array<ID,2>{2,0}));
    check(!ValidRecord(std::array<ID,1>{1}));
    std::vector<ID> oversized(limit+3,0);oversized[1]=static_cast<ID>(limit+1);check(!ValidRecord(oversized));
    std::cout<<"Queue: prune exhausted entries, head priority on bow entry/reorder, no repeated equip, failed request suppression, refill does not resurrect and save validation passed.\n";
}
