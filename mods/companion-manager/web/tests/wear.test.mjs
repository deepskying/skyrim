import {test} from 'node:test';
import assert from 'node:assert/strict';
import {fixture,simulate} from '../src/preview-data.mjs';
import {parseSnapshot,readSnapshot} from '../src/bridge.ts';
import {canToggle,headwearBlocked,isHeadwear,nextSelection,previewLabel,searchWear,wearGlyphs,wearIcon,wearOutcome,wearRows,wearSlotNames} from '../src/wear.ts';
import {defaultBehavior} from '../src/behavior.ts';
const run=(s,command,data={})=>simulate(s,{session:s.session,actorId:s.followers[0].id,command,...data});

test('every preview state has exactly one message the player can act on',()=>{
 assert.equal(previewLabel('unavailable'),'模型预览未连接');
 assert.equal(previewLabel('unsupported'),'此物品暂不支持模型预览');
 assert.equal(previewLabel('failed'),'模型加载失败');
 assert.equal(previewLabel('loading'),'正在加载模型…');
 assert.equal(previewLabel('ready'),'拖动旋转 · 滚轮缩放');
 assert.equal(previewLabel('empty'),'选择左侧的服饰预览模型');
 // An unknown status falls back to the transient state instead of claiming a broken model.
 assert.equal(previewLabel('weird'),'正在加载模型…');
 // No two states share a message: the panel must never show one where the other belongs.
 const messages=['unavailable','unsupported','failed','loading','ready','empty'].map(key=>previewLabel(key));
 assert.equal(new Set(messages).size,6);
});

test('the wear list keeps apparel only, jewelry and shields included',()=>{
 const s=fixture(),f=s.followers[0];
 const rows=wearRows(f.wardrobe);
 assert.deepEqual(rows.map(r=>r.name).sort(),['铁质护腕','铁盾','银项链','精致服装','皮甲','皮甲（火焰抗性）','铁制头盔'].sort());
 // Weapons, arrows, potions, food, ingredients, books, keys and gold never reach this page.
 for(const name of ['铁剑','铁箭','治疗药剂','苹果派','蓝山花','法术书：治疗术','住宅钥匙','金币'])
   assert.equal(rows.some(r=>r.name===name),false,name);
 // An apparel row the snapshot gave no slot mask cannot be worn, so it is not listed either.
 assert.equal(wearRows([{...f.wardrobe[1],mask:undefined}]).length,0);
 assert.equal(wearRows(undefined).length,0);
});

test('search matches names case-insensitively and ignores padding',()=>{
 const rows=wearRows(fixture().followers[0].wardrobe);
 assert.equal(searchWear(rows,'').length,rows.length);
 assert.equal(searchWear(rows,'  ').length,rows.length);
 assert.deepEqual(searchWear(rows,' 皮甲 ').map(r=>r.name),['皮甲','皮甲（火焰抗性）']);
 assert.deepEqual(searchWear(rows,'铁').map(r=>r.name).sort(),['铁盾','铁质护腕','铁制头盔'].sort());
 assert.equal(searchWear(rows,'不存在').length,0);
});

test('every row gets an icon that matches its equipment kind',()=>{
 const rows=wearRows(fixture().followers[0].wardrobe),byName=name=>rows.find(r=>r.name===name);
 // Slot first: shield, helmet and gloves are kinds of their own even when the material is armour.
 assert.deepEqual(wearIcon(byName('铁盾')),{glyph:wearGlyphs.shield,tone:'other'});
  // This load order writes a helmet as hair + circlet (0x1002), so the head bits the headwear rule
  // uses decide the glyph; the head bit alone would have drawn a plain armour icon for it.
  assert.deepEqual(wearIcon(byName('铁制头盔')),{glyph:wearGlyphs.helmet,tone:'heavy'});
  assert.deepEqual(wearIcon({...byName('铁制头盔'),mask:0x1000,armorType:'light'}),{glyph:wearGlyphs.helmet,tone:'light'});
  assert.deepEqual(wearIcon({...byName('铁制头盔'),mask:0x2}),{glyph:wearGlyphs.armor,tone:'heavy'});
 assert.deepEqual(wearIcon(byName('银项链')),{glyph:wearGlyphs.necklace,tone:'jewelry'});
 assert.deepEqual(wearIcon(byName('铁质护腕')),{glyph:wearGlyphs.gloves,tone:'heavy'});
 assert.deepEqual(wearIcon(byName('皮甲')),{glyph:wearGlyphs.armor,tone:'light'});
 assert.deepEqual(wearIcon(byName('皮甲（火焰抗性）')),{glyph:wearGlyphs.armor,tone:'light'});
 assert.deepEqual(wearIcon(byName('精致服装')),{glyph:wearGlyphs.robe,tone:'clothing'});
 // Material decides the rest: a heavy body piece, a ring by type, and anything unknown.
 const base={...byName('皮甲'),mask:4};
 assert.deepEqual(wearIcon({...base,armorType:'heavy'}),{glyph:wearGlyphs.armor,tone:'heavy'});
 assert.deepEqual(wearIcon({...base,mask:64,armorType:'jewelry'}),{glyph:wearGlyphs.ring,tone:'jewelry'});
 assert.deepEqual(wearIcon({...base,mask:0x20000,armorType:undefined}),{glyph:wearGlyphs.box,tone:'other'});
 assert.deepEqual(wearIcon({...base,mask:32,armorType:undefined}),{glyph:wearGlyphs.necklace,tone:'jewelry'});
 // The glyphs are the codepoints shipped in the shared icon font.
 assert.deepEqual(wearGlyphs,{shield:'\uE83A',armor:'\uE61D',robe:'\uEC54',necklace:'\uEA3F',ring:'\uE636',helmet:'\uE971',gloves:'\uE6C3',box:'\uE65F'});
});

test('the headwear rule matches the native one and only blocks putting a helmet on',()=>{
 const s=fixture(),f=s.followers[0],rows=wearRows(f.wardrobe);
 const helmet=rows.find(r=>r.name==='铁制头盔');
 // 30 and 42 are the head and circlet slots; hair (31), ears (43) and a robe that also covers the
 // body are deliberately not headwear, so a wig or a pair of earrings is never taken off with it.
 assert.equal(helmet.mask,0x1002);
 assert.ok(isHeadwear(helmet));
 assert.ok(isHeadwear({...helmet,mask:0x1}));
 assert.ok(isHeadwear({...helmet,mask:0x1000}));
 assert.equal(isHeadwear({...helmet,mask:0x2}),false);
 assert.equal(isHeadwear({...helmet,mask:0x2000}),false);
 assert.equal(isHeadwear({...helmet,mask:0x800000}),false);
 assert.equal(isHeadwear({...helmet,mask:0x1006}),false);
 assert.equal(isHeadwear({...helmet,mask:4}),false);
 // Only the "wear" direction is refused: the piece the companion already has on stays clickable.
 assert.equal(headwearBlocked(helmet,false),true);
 assert.equal(headwearBlocked({...helmet,equipped:true},false),false);
 assert.equal(headwearBlocked(helmet,true),false);
 // The simulated native side answers the same way, and turning the rule on takes a worn helmet off
 // at once instead of at the next equip.
 const save=extra=>simulate(s,{session:s.session,actorId:f.id,command:'behavior',settings:{...defaultBehavior,...extra}});
 helmet.equipped=true;
 assert.ok(save({helmet:false}).ok);
 assert.equal(helmet.equipped,false);
 assert.ok(helmet.favorite===false);
 const refused=simulate(s,{session:s.session,actorId:f.id,command:'toggleWear',itemKey:helmet.key});
 assert.equal(refused.ok,false);assert.match(refused.message,/禁止这位伙伴佩戴头盔/);
 assert.ok(save({helmet:true}).ok);
 assert.ok(simulate(s,{session:s.session,actorId:f.id,command:'toggleWear',itemKey:helmet.key}).ok);
 assert.equal(helmet.equipped,true);
});

test('arrow navigation stays inside the list and starts at the first row',()=>{
 assert.equal(nextSelection(-1,5,1),0);
 assert.equal(nextSelection(-1,5,-1),0);
 assert.equal(nextSelection(0,5,-1),0);
 assert.equal(nextSelection(4,5,1),4);
 assert.equal(nextSelection(2,5,1),3);
 assert.equal(nextSelection(2,5,-1),1);
 assert.equal(nextSelection(0,0,1),-1);
 assert.equal(nextSelection(-1,0,1),-1);
});

test('the preview reports the armor total the click will leave behind',()=>{
 const rows=wearRows(fixture().followers[0].wardrobe),byName=name=>rows.find(r=>r.name===name);
 const body=byName('皮甲'),spare=byName('皮甲（火焰抗性）'),necklace=byName('银项链'),bracers=byName('铁质护腕');
 assert.equal(rows.reduce((t,r)=>t+(r.equipped?(r.armorRating??0):0),0),36); // 皮甲 26 + 护腕 10
 // A same-slot swap replaces the worn piece instead of stacking on top of it.
 const swap=wearOutcome(rows,spare);
 assert.equal(swap.action,'wear');assert.equal(swap.current,36);assert.equal(swap.next,36);
 assert.equal(swap.delta,0);assert.deepEqual(swap.replaced.map(r=>r.name),['皮甲']);
 // A piece in a free slot only adds its own rating.
 assert.equal(wearOutcome(rows,necklace).delta,0);
 assert.equal(wearOutcome(rows,necklace).next,36);
 // Taking something off subtracts exactly that piece.
 assert.deepEqual(wearOutcome(rows,body),{action:'takeOff',current:36,next:10,delta:-26,replaced:[]});
 assert.deepEqual(wearOutcome(rows,bracers).next,26);
 // Every piece of the comparison is optional on the wire.
 const bare=[{...body,armorRating:undefined,equipped:false}];
 assert.equal(wearOutcome(bare,bare[0]).delta,0);
});

test('the armor comparison shows whole points that add up',()=>{
 // Live ratings are floats, so the page rounds them; the three numbers must stay consistent.
 const rows=wearRows(fixture().followers[0].wardrobe).map(r=>({...r}));
 const body=rows.find(r=>r.name==='皮甲'),spare=rows.find(r=>r.name==='皮甲（火焰抗性）');
 body.armorRating=729.6899909973145;spare.armorRating=741.31;
 rows.find(r=>r.name==='铁质护腕').armorRating=204.9;
 const total=wearOutcome(rows,spare);
 assert.equal(total.current,935);            // 729.69 + 204.9
 assert.equal(total.next,946);               // 741.31 + 204.9
 assert.equal(total.delta,11);
 assert.equal(total.current+total.delta,total.next);
 const off=wearOutcome(rows,{...body,equipped:true});
 assert.equal(off.action,'takeOff');assert.equal(off.next,205);assert.equal(off.delta,-730);
 assert.equal(off.current+off.delta,off.next);
 for(const value of [total.current,total.next,total.delta,off.current,off.next,off.delta])
  assert.equal(Number.isInteger(value),true);
});

test('quest gear can be put on but never taken off',()=>{
 const rows=wearRows(fixture().followers[0].wardrobe);
 for(const row of rows) assert.equal(canToggle(row),true);
 assert.equal(canToggle({...rows[0],equipped:true,quest:true}),false);
 assert.equal(canToggle({...rows[0],equipped:false,quest:true}),true);
});

test('toggleWear swaps one instance, keeps the slots correct and protects quest gear',()=>{
 const s=fixture(),f=s.followers[0],rows=wearRows(f.wardrobe),byName=name=>rows.find(r=>r.name===name);
 // The robe covers body and feet, so it may only take the body armor off here.
 assert.ok(run(s,'toggleWear',{itemKey:byName('精致服装').key}).ok);
 assert.equal(byName('精致服装').equipped,true);
 assert.equal(byName('皮甲').equipped,false);
 assert.equal(byName('铁质护腕').equipped,true);
 // Clicking a worn piece takes that exact instance off.
 assert.ok(run(s,'toggleWear',{itemKey:byName('铁质护腕').key}).ok);
 assert.equal(byName('铁质护腕').equipped,false);
 assert.equal(byName('皮甲').equipped,false);
 // A quest piece cannot be removed, and the request changes nothing.
 const body=byName('精致服装');body.quest=true;
 assert.equal(run(s,'toggleWear',{itemKey:body.key}).ok,false);
 assert.equal(body.equipped,true);
 // A protected worn piece blocks the swap into its slot instead of being stripped.
 const spare=byName('皮甲（火焰抗性）');
 assert.equal(run(s,'toggleWear',{itemKey:spare.key}).ok,false);
 assert.equal(spare.equipped,false);assert.equal(body.equipped,true);
 // Once it stops being protected it comes off like any other piece.
 body.quest=false;
 assert.ok(run(s,'toggleWear',{itemKey:body.key}).ok);
 assert.equal(body.equipped,false);
 assert.equal(run(s,'toggleWear',{itemKey:'00000000:00000000:0000'}).ok,false);
 assert.equal(run(s,'toggleWear',{itemKey:'00012EB7:00000014:0001'}).ok,false); // a weapon is not apparel
 assert.ok(parseSnapshot(s));
});

test('wear fields are validated and repaired instead of blanking the panel',()=>{
 const s=fixture(),row=s.followers[0].wardrobe[1];
 for(const bad of [0,-1,1.5,0x100000000]){const c=structuredClone(s);c.followers[0].wardrobe[1].mask=bad;assert.equal(parseSnapshot(c),null);}
 for(const bad of [-1,Number.POSITIVE_INFINITY,'x']){const c=structuredClone(s);c.followers[0].wardrobe[1].armorRating=bad;assert.equal(parseSnapshot(c),null);}
 {const c=structuredClone(s);c.followers[0].wardrobe[1].armorType='shield';assert.equal(parseSnapshot(c),null);}
 for(const type of ['light','heavy','jewelry','clothing','other']){const c=structuredClone(s);c.followers[0].wardrobe[1].armorType=type;assert.ok(parseSnapshot(c));}
 {const c=structuredClone(s);c.followers[0].wardrobe[1].enchantment=123;assert.equal(parseSnapshot(c),null);}
 // Repair drops the unusable value but keeps the item listed.
 const broken={...structuredClone(s),followers:structuredClone(s.followers).map(f=>({...f,wardrobe:f.wardrobe.map(x=>x.key===row.key?{...x,armorRating:-5,armorType:'shield'}:x)}))};
 const {snapshot,issues}=readSnapshot(broken);
 assert.ok(snapshot);assert.ok(issues.some(text=>text.includes('数值无法读取')));
 const kept=snapshot.followers[0].wardrobe.find(x=>x.key===row.key);
 assert.equal(kept.armorRating,undefined);assert.equal(kept.armorType,undefined);assert.equal(kept.mask,row.mask);
});
