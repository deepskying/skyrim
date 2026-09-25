import {test} from 'node:test';
import assert from 'node:assert/strict';
import {fixture,simulate} from '../src/preview-data.mjs';
import {parseSnapshot,readSnapshot} from '../src/bridge.ts';
import {outfitSlots,validOutfits} from '../src/outfits.ts';
const run=(s,command,data={})=>simulate(s,{session:s.session,actorId:s.followers[0].id,command,...data});
test('outfit snapshot accepts slot 61 and rejects malformed saved items and duplicate presets',()=>{
 const s=fixture();assert.ok(parseSnapshot(s));
 assert.deepEqual(outfitSlots(0x80000004),[32,61]);
 for(const bad of [-1,0,0x100000000,1.5]){const d=structuredClone(s.followers[0].outfits);d.items[0].mask=bad;assert.equal(validOutfits(d),false);}
 s.followers[0].outfits.presets.push(structuredClone(s.followers[0].outfits.presets[0]));assert.equal(parseSnapshot(s),null);
});
test('the player card carries its own outfit payload and survives repair',()=>{
  const s=fixture();
  s.self={id:'00000014',name:'抓根宝',outfits:structuredClone(s.followers[0].outfits),presetCount:1};
  assert.ok(parseSnapshot(s));
  const bad=structuredClone(s);bad.self.outfits.items[0].mask=-1;assert.equal(parseSnapshot(bad),null);
  const repaired=readSnapshot({...structuredClone(s),self:{id:'nope',name:'x'}});
  assert.equal(repaired.snapshot.self,undefined);
  assert.ok(repaired.issues.some(text=>text.includes('玩家穿搭')));
});
test('named save captures current instances, favorites them and isolates the companion',()=>{
 const s=fixture(),f=s.followers[0],other=structuredClone(s.followers[1]);
 f.outfits.items[0].favorite=false;
 assert.ok(run(s,'saveNamedOutfit',{name:'旅行装'}).ok);
 const saved=f.outfits.presets.find(p=>p.name==='旅行装');assert.ok(saved);
 assert.deepEqual(saved.items.map(i=>i.key),f.outfits.items.filter(i=>i.equipped).map(i=>i.key));
 assert.ok(saved.items.every(i=>i.favorite));assert.deepEqual(s.followers[1],other);
 assert.equal(run(s,'saveNamedOutfit',{name:'旅行装'}).ok,false);assert.ok(parseSnapshot(s));
});
test('removing a saved outfit leaves worn items and favorites unchanged',()=>{
 const s=fixture(),f=s.followers[0],other=structuredClone(s.followers[1].outfits);
 assert.ok(run(s,'saveNamedOutfit',{name:'旅行装'}).ok);
 const preset=f.outfits.presets.find(p=>p.name==='旅行装');
 const items=structuredClone(f.outfits.items);
 assert.equal(run(s,'removeNamedOutfit',{presetId:999999}).ok,false);
 assert.equal(run(s,'removeNamedOutfit',{presetId:'1'}).ok,false);
 assert.ok(run(s,'removeNamedOutfit',{presetId:preset.id}).ok);
 assert.equal(f.outfits.presets.some(p=>p.id===preset.id),false);
 assert.deepEqual(f.outfits.items,items);
 assert.deepEqual(s.followers[1].outfits,other);
 assert.equal(run(s,'removeNamedOutfit',{presetId:preset.id}).ok,false);
 assert.ok(parseSnapshot(s));
});
test('saved outfit skips a missing instance instead of wearing another enchanted copy',()=>{
  const s=fixture(),f=s.followers[0];run(s,'saveNamedOutfit',{name:'原装'});
  const p=f.outfits.presets.find(p=>p.name==='原装');
  const original=f.outfits.items[0];original.equipped=false;original.available=false;
  const replacement=f.outfits.items[1];replacement.equipped=true;
  assert.ok(run(s,'applyNamedOutfit',{presetId:p.id}).ok);
  // The set names the missing instance, so neither it nor the stand-in copy stays on top of it.
  assert.equal(original.equipped,false);assert.equal(replacement.equipped,false);
});
test('multi-slot clothes replace both body and feet; protection in either slot blocks them',()=>{
 const s=fixture(),d=s.followers[0].outfits,robe=d.items[2],boots=d.items[3];
 boots.quest=true;assert.equal(run(s,'outfitPart',{slot:32,itemKey:robe.key}).ok,false);
 boots.quest=false;assert.ok(run(s,'outfitPart',{slot:32,itemKey:robe.key}).ok);
 assert.equal(robe.equipped,true);assert.equal(boots.equipped,false);assert.equal(d.items[0].equipped,false);
 assert.equal(run(s,'outfitPart',{slot:39}).ok,false);assert.equal(run(s,'outfitPart',{slot:62}).ok,false);
});
test('probability boundaries and no saved sets choose valid paths',()=>{
 const s=fixture(),f=s.followers[0];s.settings.savedOutfitChance=100;
 assert.ok(run(s,'changeOutfit').ok);assert.equal(f.outfits.items[2].equipped,true);
 f.outfits.presets=[];assert.ok(run(s,'changeOutfit').ok);
 s.settings.savedOutfitChance=101;assert.equal(parseSnapshot(s),null);
});
test('unequip addresses the exact worn instance and supports hidden multi-slot clothes',()=>{
 const s=fixture(),d=s.followers[0].outfits,robe=d.items[2];
 run(s,'outfitPart',{slot:32,itemKey:robe.key});robe.hidden=true;robe.available=false;
 const necklace=d.items[5];assert.equal(necklace.equipped,true);
 assert.ok(run(s,'unequipOutfitPart',{slot:37,itemKey:robe.key}).ok);
 assert.equal(robe.equipped,false);assert.equal(necklace.equipped,true);
 assert.equal(run(s,'unequipOutfitPart',{slot:32,itemKey:robe.key}).ok,false);
});
test('unequip rejects protected equipment, wrong slots and pending changes',()=>{
  const s=fixture(),d=s.followers[0].outfits,body=d.items[0];
  body.quest=true;assert.equal(run(s,'unequipOutfitPart',{slot:32,itemKey:body.key}).ok,false);
  body.quest=false;assert.equal(run(s,'unequipOutfitPart',{slot:37,itemKey:body.key}).ok,false);
  d.pending=true;assert.equal(run(s,'unequipOutfitPart',{slot:32,itemKey:body.key}).ok,false);
  assert.equal(body.equipped,true);
});
test('random piece and whole-set changes draw on favorites only',()=>{
  const s=fixture(),d=s.followers[0].outfits,spareBody=d.items[1],robe=d.items[2],spareFeet=d.items[4];
  assert.equal(robe.favorite,false);
  // The in-slot random button skips the unfavorited robe even though it covers the same slot.
  assert.ok(run(s,'outfitPart',{slot:32}).ok);
  assert.equal(spareBody.equipped,true);assert.equal(robe.equipped,false);
  robe.equipped=false;spareBody.equipped=false;d.items[0].equipped=true;
  spareBody.favorite=false;spareFeet.favorite=false;d.presets=[];
  // Recombining without any spare favorite leaves the outfit alone instead of wearing raw stock.
  assert.ok(run(s,'changeOutfit').ok);
  assert.equal(robe.equipped,false);assert.equal(spareFeet.equipped,false);assert.equal(d.items[0].equipped,true);
  assert.equal(run(s,'outfitPart',{slot:32,itemKey:robe.key}).ok,true); // explicit picks stay manual
});
test('applying a saved outfit takes off the pieces it does not name',()=>{
  const s=fixture(),d=s.followers[0].outfits,body=d.items[0],robe=d.items[2],boots=d.items[3],necklace=d.items[5];
  necklace.quest=true; // quest gear is protected and stays on
  assert.ok(run(s,'applyNamedOutfit',{presetId:1}).ok);
  assert.equal(robe.equipped,true);
  assert.equal(body.equipped,false);assert.equal(boots.equipped,false); // not in the set: taken off
  assert.equal(necklace.equipped,true);
  // Saving what is worn now records exactly the mixed result the player sees.
  assert.ok(run(s,'saveNamedOutfit',{name:'替换后'}).ok);
  const saved=d.presets.find(p=>p.name==='替换后');
  assert.deepEqual(saved.items.map(i=>i.key).sort(),[necklace.key,robe.key].sort());
});
