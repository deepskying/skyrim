import {test} from 'node:test';
import assert from 'node:assert/strict';
import {fixture,simulate} from './fixture.mjs';
import {validBehavior,defaultBehavior,validWardrobe,selectionTotals} from '../src/behavior.ts';
import {parseSnapshot} from '../src/bridge.ts';
test('behavior defaults and exact inventory instances validate; duplicate keys and invalid values are rejected',()=>{
 const s=fixture();assert.ok(parseSnapshot(s));assert.ok(validBehavior(defaultBehavior));
 assert.equal(validBehavior({...defaultBehavior,radius:4}),false);
 assert.equal(validBehavior({...defaultBehavior,outfitHours:1.5}),false);
 // Headwear ships off by default and every behaviour payload carries the key.
 assert.equal(defaultBehavior.helmet,false);
 assert.equal(validBehavior({...defaultBehavior,helmet:undefined}),false);
 const w=s.followers[0].wardrobe;assert.ok(validWardrobe(w));assert.equal(validWardrobe([...w,w[0]]),false);
 w[0].weight=NaN;assert.equal(parseSnapshot(s),null);
});
test('favoriting a specific enchanted copy leaves the other copy unchanged',()=>{
 const s=fixture(),f=s.followers[0],copy=f.wardrobe[2],original=f.wardrobe[1];
 assert.equal(copy.id,original.id);assert.notEqual(copy.key,original.key);
 assert.ok(simulate(s,{session:s.session,command:'favorite',actorId:f.id,itemKey:copy.key,value:true}).ok);
 assert.ok(copy.favorite);assert.ok(original.favorite);
 simulate(s,{session:s.session,command:'favorite',actorId:f.id,itemKey:copy.key,value:false});
 assert.ok(original.favorite);assert.equal(copy.favorite,false);
});
test('default changes preserve personal overrides and inherit can restore default policy',()=>{
 const s=fixture(),f=s.followers[0],r={session:s.session,actorId:f.id};
 simulate(s,{...r,command:'behavior',settings:{...defaultBehavior,sell:false}});
 simulate(s,{...r,command:'behaviorDefaults',settings:{...defaultBehavior,radius:20}});
 assert.equal(f.behavior.sell,false);assert.equal(f.behavior.radius,40);
 simulate(s,{...r,command:'behavior',inherit:true});assert.equal(f.behavior.radius,20);assert.equal(f.behaviorOverride,false);
});
test('potions, food and miscellaneous stacks can be locked and unlocked without changing their quantity',()=>{
 const s=fixture(),f=s.followers[0];
 for(const name of ['治疗药剂','苹果派','铁锭']) {
  const item=f.wardrobe.find(i=>i.name===name),count=item.count;
  assert.equal(item.equipment,false);
  const request={session:s.session,command:'favorite',actorId:f.id,itemKey:item.key};
  assert.equal(simulate(s,{...request,value:true}).ok,true);
  assert.equal(item.favorite,true);assert.equal(item.count,count);
  assert.equal(simulate(s,{...request,value:false}).ok,true);
  assert.equal(item.favorite,false);assert.equal(item.count,count);
 }
 assert.ok(parseSnapshot(s));
});
test('multi-item handover rejects overweight and worn items without partially changing inventory',()=>{
 const s=fixture(),f=s.followers[0],r={session:s.session,actorId:f.id,command:'wardrobeTake'};
 const item=f.wardrobe[5];s.automation.playerCarried=299;
 const before=structuredClone(s);
 assert.equal(simulate(s,{...r,items:[{key:item.key,count:2}]}).ok,false);assert.deepEqual(s,before);
 assert.equal(simulate(s,{...r,items:[{key:f.wardrobe[0].key,count:1}]}).ok,false);assert.deepEqual(s,before);
 assert.ok(simulate(s,{...r,items:[{key:item.key,count:1}]}).ok);assert.equal(s.automation.playerCarried,300);assert.equal(item.count,11);
 const totals=selectionTotals(f.wardrobe,{[item.key]:3});assert.deepEqual(totals,{weight:3,value:21,count:3});
});
