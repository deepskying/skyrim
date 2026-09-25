#include "craft_order_rules.h"
#include <iostream>
#include <stdexcept>
using namespace craft_order_rules;
using crafting::Stack;
#define check(expr) do{if(!(expr)){std::fprintf(stderr,"FAIL line %d: %s\n",__LINE__,#expr);std::fflush(stderr);throw std::runtime_error("craft order assertion failed");}}while(0)
Entry Batch(std::uint32_t spell,int count,int charge=10,int mana=12,int gold=5){
    Entry e;e.spell=spell;e.arrow=spell+0x100;e.total=count;e.remaining=count;
    e.chargePerArrow=charge;e.manaPerArrow=mana;e.goldPerArrow=gold;return e;
}
int main(){
    std::vector<Entry> queue;
    check(Accept(queue,1,999));
    check(!Accept(queue,1,0));
    check(Accept(queue,1,perSpellLimit));             // the queue ceiling is inclusive
    check(!Accept(queue,1,perSpellLimit+1));

    auto first=Batch(1,10);
    first.bases={{100,6,0},{101,4,0}};
    first.materials={{203,3,50},{204,2,25}};
    Add(queue,first);
    auto second=Batch(2,5);
    Add(queue,second);
    check(queue.size()==2&&queue[0].spell==1&&queue[1].spell==2);
    // Merging a later batch of the same spell keeps its original queue position.
    auto merge=Batch(1,4);
    merge.bases={{100,4,0}};
    merge.materials={{203,2,50}};
    Add(queue,merge);
    check(queue.size()==2&&queue[0].spell==1&&queue[1].spell==2);
    check(queue[0].total==14&&queue[0].remaining==14);
    check(queue[0].bases.size()==2&&queue[0].bases[0].count==10&&queue[0].bases[1].count==4);
    check(queue[0].materials.size()==2&&queue[0].materials[0].count==5&&queue[0].materials[1].count==2);
    check(Queued(queue,1)==14&&Queued(queue,3)==0);
    check(!Accept(queue,1,perSpellLimit)&&Accept(queue,3,perSpellLimit));

    check(Progress(queue[0])==1.0);
    check(Advance(queue[0])&&queue[0].remaining==13);
    check(std::abs(Progress(queue[0])-13.0/14.0)<1e-9);
    // Bases are consumed from the front, so the refund returns the tail of the list.
    check(RefundBases(queue[0]).size()==1&&RefundBases(queue[0])[0].id==101&&RefundBases(queue[0])[0].count==1);
    // Charge is spent per arrow from the front of the basket: one arrow spent one bottle.
    const auto materials=RefundMaterials(queue[0]);
    check(materials.size()==2&&materials[0].id==203&&materials[0].count==4&&materials[1].count==2);
    check(RefundGold(queue[0])==13*5);
    for (int i=0;i<13;++i) check(Advance(queue[0])==(i<12));
    check(queue[0].remaining==0&&!Advance(queue[0]));
    check(RefundBases(queue[0]).size()==2&&RefundBases(queue[0])[0].count==4);
    check(RefundMaterials(queue[0])[0].count==2&&RefundGold(queue[0])==0);

    check(CountLabel(1)=="1"&&CountLabel(99)=="99"&&CountLabel(999)=="999");
    check(CountLabel(1000)=="1K"&&CountLabel(1500)=="1.5K"&&CountLabel(4500)=="4.5K"&&CountLabel(10000)=="10K");
    check(CountLabel(-5)=="0");

    check(Evaluate(false,false,false,false,true)==Pause::none);
    check(Evaluate(true,false,false,false,true)==Pause::panel);
    check(Evaluate(false,true,false,false,true)==Pause::loading);
    check(Evaluate(true,true,true,true,true)==Pause::loading);
    check(Evaluate(false,false,true,false,true)==Pause::dead);
    check(Evaluate(false,false,false,true,true)==Pause::combat);
    check(Evaluate(false,false,false,true,false)==Pause::none); // the switch disables the combat pause
    check(std::string(Reason(Pause::combat))=="战斗中暂停"&&std::string(Reason(Pause::none)).empty());

    // Co-save round trip, including an unresolved spell that must be dropped for a refund.
    std::vector<Entry> saved;
    auto one=Batch(0x1000,300,20,30,5);one.bases={{100,200,0},{101,100,0}};one.materials={{203,4,50}};
    auto two=Batch(0x2000,50,8,12,4);two.bases={{102,50,0}};two.materials={{204,1,100}};
    Add(saved,one);Add(saved,two);Advance(saved[0]);
    const auto words=Encode(saved);
    std::vector<Entry> restored;
    auto resolve=[](std::uint32_t id,std::uint32_t& out){if (id==0x1000||id==0x1100||id==0x2000||id==0x2100) { out=id; return true; } out=0; return false; };
    check(Decode(words,restored,resolve)&&restored.size()==2);
    check(restored[0].total==300&&restored[0].remaining==299&&restored[0].manaPerArrow==30);
    check(restored[0].bases.size()==2&&restored[0].bases[0].count==200&&restored[0].materials[0].count==4);
    check(RefundGold(restored[0])==299*5&&Progress(restored[1])==1.0);
    std::vector<Entry> dropped;
    auto missing=[](std::uint32_t,std::uint32_t& out){out=0;return false;};
    check(Decode(words,dropped,missing)&&dropped.empty());
    std::vector<std::uint32_t> truncated(words.begin(),words.end()-1);
    check(!Decode(truncated,dropped,resolve));
    std::vector<std::uint32_t> wrongVersion=words;wrongVersion[0]=9;
    check(!Decode(wrongVersion,dropped,resolve));

    std::cout<<"Craft order: ceilings, in-place merge, per-arrow progress, refunds, HUD labels, pause precedence and co-save round trip passed.\n";
}
