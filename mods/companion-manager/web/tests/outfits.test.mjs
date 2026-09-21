import {test} from 'node:test';
import assert from 'node:assert/strict';
import {fixture,simulate} from '../src/preview-data.mjs';
import {parseSnapshot} from '../src/bridge.ts';
import {outfitSlots,validOutfits} from '../src/outfits.ts';
const run=(s,command,data={})=>simulate(s,{session:s.session,actorId:s.followers[0].id,command,...data});
test('outfit snapshot accepts slot 61 and rejects malformed saved items and duplicate presets',()=>{
 const s=fixture();assert.ok(parseSnapshot(s));
 assert.deepEqual(outfitSlots(0x80000004),[32,61]);
 for(const bad of [-1,0,0x100000000,1.5]){const d=structuredClone(s.followers[0].outfits);d.items[0].mask=bad;assert.equal(validOutfits(d),false);}
 s.followers[0].outfits.presets.push(structuredClone(s.followers[0].outfits.presets[0]));assert.equal(parseSnapshot(s),null);
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
test('saved outfit skips missing instance without equipping another enchanted copy or clearing that slot',()=>{
 const s=fixture(),f=s.followers[0];run(s,'saveNamedOutfit',{name:'原装'});
 const p=f.outfits.presets.find(p=>p.name==='原装');
 const original=f.outfits.items[0];original.equipped=false;original.available=false;
 const replacement=f.outfits.items[1];replacement.equipped=true;
 assert.ok(run(s,'applyNamedOutfit',{presetId:p.id}).ok);assert.equal(replacement.equipped,true);assert.equal(original.equipped,false);
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
