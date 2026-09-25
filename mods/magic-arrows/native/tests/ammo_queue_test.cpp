#include "ammo_queue_rules.h"
#include <array>
#include <unordered_map>
#include <stdexcept>
#include <iostream>
using namespace ammo_queue_rules;
void check(bool b){if(!b)throw std::runtime_error("queue regression");}
int main(){
    {
        for(ID mode=0;mode<3;++mode)check(ValidRecord(std::array<ID,4>{mode,2,10,30},2));
        check(!ValidRecord(std::array<ID,2>{3,0},2));
        check(!ValidRecord(std::array<ID,2>{0,0},3));
    }

    {
        std::vector<ID> selected{10,20};Tracker priority;
        auto available=[](ID){return 1;};
        check(priority.Tick(selected,30,available)==10);
        check(Promote(selected,30));priority.Reset();
        check((selected==std::vector<ID>{30,10,20}));
        check(priority.Tick(selected,30,available)==0); // manual choice stays equipped
        check(Promote(selected,20));priority.Reset();
        check((selected==std::vector<ID>{20,30,10}));
        check(Promote(selected,20)&&selected.size()==3); // no duplicate
        check(Prune(selected,[](ID id){return id==20?0:1;}));priority.Reset();
        check(priority.Tick(selected,20,available)==30); // exhaustion resumes old order
        selected.clear();check(Promote(selected,99)&&selected.front()==99);
        selected.clear();for(ID id=1;id<=limit;++id)selected.push_back(id);
        const auto full=selected;
        check(!Promote(selected,0)&&selected==full);
        check(Promote(selected,64)&&selected.front()==64&&selected.size()==limit);
        check(Contains(selected,1)); // existing entry promotion ejects nothing
        selected=full;
        check(Promote(selected,1000)&&selected.size()==limit);
        check(selected.front()==1000&&!Contains(selected,64));
        for(ID i=1;i<limit;++i)check(selected[i]==i); // only the old tail leaves
        check(Promote(selected,1000)&&selected.size()==limit&&Contains(selected,63));
    }
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
