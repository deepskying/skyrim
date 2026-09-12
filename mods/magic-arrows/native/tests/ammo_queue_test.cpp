#include "ammo_queue_rules.h"
#include <array>
#include <unordered_map>
#include <stdexcept>
#include <iostream>
using namespace ammo_queue_rules;
void check(bool b){if(!b)throw std::runtime_error("queue regression");}
int main(){
    std::array<ID,4> order{10,20,30,40};std::unordered_map<ID,int> stock{{10,2},{20,0},{30,4},{40,1}};
    auto count=[&](ID id){return stock[id];};Tracker t;
    check(Next(order,0,[&](ID id){return count(id)>0;})==10);
    t.Observe(10,2,order);stock[10]=0;
    // The game already equipped an arbitrary 99 by the time the poll executes.
    check(t.Tick(order,99,count)==30);check(t.Tick(order,99,count)==0);
    t.Reset();t.Observe(30,4,order);stock[30]=0;check(t.Tick(order,10,count)==40);
    t.Reset();t.Observe(40,1,order);stock[40]=0;stock[10]=10;
    check(t.Tick(order,10,count)==0&&t.finished);check(t.Tick(order,10,count)==0); // no wrap
    t.Reset();stock[30]=3;t.Observe(10,10,order);
    check(t.Tick(order,99,count)==0&&t.watched==0); // manual outside selection wins
    check(t.Tick(order,30,count)==0&&t.watched==30); // manual queued selection becomes cursor
    std::array<ID,4> reordered{10,40,30,20};stock[20]=2;stock[30]=0;
    check(t.Tick(reordered,99,count)==20); // current entry follows the new order
    t.Reset();check(t.Tick(order,0,count)==0); // load/disable cannot reuse previous depletion
    check(Next(order,99,[&](ID){return true;})==0);
    check(Next(std::span<const ID>{},0,[&](ID){return true;})==0);
    check(ValidRecord(std::array<ID,4>{1,2,10,30}));
    check(ValidRecord(std::array<ID,2>{0,0}));
    check(!ValidRecord(std::array<ID,4>{1,3,10,30}));
    check(!ValidRecord(std::array<ID,2>{2,0}));
    check(!ValidRecord(std::array<ID,1>{1}));
    std::vector<ID> oversized(limit+3,0);oversized[1]=static_cast<ID>(limit+1);check(!ValidRecord(oversized));
    std::cout<<"Queue: ordered depletion, game auto-selection, missing stock, no wrap, manual override, reorder, reset and single dispatch passed.\n";
}
