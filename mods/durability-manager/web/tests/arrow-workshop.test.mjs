import assert from 'node:assert/strict';
import test from 'node:test';
import { readFileSync } from 'node:fs';
import ts from 'typescript';
async function module(name) {
  const source = readFileSync(new URL(`../src/arrows/${name}.ts`, import.meta.url), 'utf8');
  const js = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.ESNext } }).outputText;
  return import(`data:text/javascript;base64,${Buffer.from(js).toString('base64')}`);
}
const { planCraft, matchingMaterials, materialHighlight, moveQueue, matchesCraftReply } = await module('rules');
const { arrowDemo: state } = await module('demo');
const selection = { spell: 101, bases: [{ id: 10, count: 5 }], materials: [{ id: 201, count: 1 }] };

test('crafting requires the matching nearby station and fails closed before state arrives', async () => {
  const { craftingAccessError } = await module('rules');
  for (const normal of [false, true]) {
    assert.notEqual(craftingAccessError({ ...state, craftingAccess: undefined }, normal), '');
    assert.notEqual(craftingAccessError({ ...state, loaded: false }, normal), '');
    assert.equal(craftingAccessError(state, normal), '');
  }
  const enchanting = { ...state, craftingAccess: { magic: true, normal: false } };
  const forge = { ...state, craftingAccess: { magic: false, normal: true } };
  assert.equal(craftingAccessError(enchanting, false), '');
  assert.match(craftingAccessError(enchanting, true), /铁匠|锻造炉/);
  assert.equal(craftingAccessError(forge, true), '');
  assert.match(craftingAccessError(forge, false), /附魔台/);
  // A fresh snapshot after walking away must revoke both permissions.
  const away = { ...state, craftingAccess: { magic: false, normal: false } };
  assert.notEqual(craftingAccessError(away, false), '');
  assert.notEqual(craftingAccessError(away, true), '');
});
test('matching potions precede raw ingredients and unsupported families never charge', () => {
  const before = JSON.stringify(state.materials);
  assert.deepEqual(matchingMaterials(state.materials, state.spells[0]).map(m => m.id), [201, 202, 203]);
  assert.deepEqual(matchingMaterials(state.materials, state.spells[1]).map(m => m.id), [204]);
  assert.equal(JSON.stringify(state.materials), before);
});
test('spell borders follow enough matching charge, with prepared mixtures above raw ingredients', () => {
  const fire = state.spells[0], ice = state.spells[1];
  assert.equal(materialHighlight(state.materials, fire), 'potion');
  assert.equal(materialHighlight(state.materials, ice), 'potion');
  assert.equal(materialHighlight([{ id: 1, name: '火盐', kind: 'ingredient', count: 2, charges: { fire: 8 } }], fire), 'ingredient');
  assert.equal(materialHighlight([{ id: 1, name: '抗火药水', kind: 'potion', count: 1, charges: { fire: 1 } }, { id: 2, name: '火盐', kind: 'ingredient', count: 1, charges: { fire: 10 } }], fire), 'potion');
  assert.equal(materialHighlight([{ id: 1, name: '火盐', kind: 'ingredient', count: 1, charges: { fire: 8 } }], fire), '');
  assert.equal(materialHighlight([{ id: 1, name: '抗冰药水', kind: 'potion', count: 2, charges: { ice: 50 } }], fire), '');
  assert.equal(materialHighlight(state.materials, state.spells[3]), '');
});
test('potion and mixed-base plan computes output and costs without consuming inventory', () => {
  const before = JSON.stringify(state);
  const p = planCraft(state, selection);
  assert.equal(p.error, ''); assert.equal(p.total, 5); assert.equal(p.energy, 50); assert.equal(p.gold, 25); assert.equal(p.mana, 60);
  const partial = planCraft(state, { ...selection, bases: [{ id: 10, count: 4 }, { id: 11, count: 4 }] });
  assert.equal(partial.total, 5); assert.equal(partial.target, 8);
  assert.equal(JSON.stringify(state), before);
});
test('invalid quantities, depleted materials, duplicate ids and mismatched potions fail closed', () => {
  for (const bases of [[{ id: 10, count: 49 }], [{ id: 10, count: 0 }], [{ id: 10, count: 1.5 }], [{ id: 10, count: NaN }], [{ id: 10, count: 1 }, { id: 10, count: 1 }], [{ id: 21, count: 1 }]]) assert.notEqual(planCraft(state, { ...selection, bases }).error, '');
  for (const materials of [[{ id: 204, count: 1 }], [{ id: 201, count: 5 }], [{ id: 201, count: 1 }, { id: 201, count: 1 }]]) assert.notEqual(planCraft(state, { ...selection, materials }).error, '');
  assert.equal(planCraft({ ...state, resources: { gold: 0, magicka: 220 } }, selection).error, '金币不足');
});
test('late quotes and commit receipts cannot authorize another selection or request', () => {
  const request = { id: 3, key: 'selection-b', type: 'quote' }, reply = { requestID: 3, type: 'quote', ok: true };
  assert.equal(matchesCraftReply(request, 'selection-b', reply), true);
  assert.equal(matchesCraftReply(request, 'selection-a', reply), false);
  assert.equal(matchesCraftReply(request, 'selection-b', { ...reply, requestID: 2 }), false);
  assert.equal(matchesCraftReply(request, 'selection-b', { ...reply, type: 'craft' }), false);
  assert.equal(matchesCraftReply(undefined, 'selection-b', reply), false);
});
test('queue reorder keeps each entry exactly once and ignores missing targets', () => {
  const ids = [21, 10, 11];
  assert.deepEqual(moveQueue(ids, 11, 21), [11, 21, 10]);
  assert.deepEqual(moveQueue(ids, 21, 11), [10, 11, 21]);
  assert.deepEqual(moveQueue(ids, 9, 11), ids); assert.deepEqual(ids, [21, 10, 11]);
});
test('unified package has one view and no debug supply or page handoff', () => {
  const native = readFileSync(new URL('../../../magic-arrows/native/src/main.cpp', import.meta.url), 'utf8');
  const pack = readFileSync(new URL('../../../workshop/packaging/package.py', import.meta.url), 'utf8');
  assert.doesNotMatch(native, /type=="supply"|PendingWorkshop|RequestWorkshop/);
  assert.match(native, /#ifndef UNIFIED_WORKSHOP\s+view=api->CreateView/);
  assert.doesNotMatch(pack, /arrow-shell|PrismaUI\/views\/MagicArrows/);
  const app = readFileSync(new URL('../src/App.tsx', import.meta.url), 'utf8');
  assert.doesNotMatch(app, /location.assign|<iframe/);
});

test('manual equip promotes ordinary arrows before closing and requesting equip', () => {
  const native = readFileSync(new URL('../../../magic-arrows/native/src/main.cpp', import.meta.url), 'utf8');
  const equip = native.slice(native.indexOf('}else if(type=="equip"){'), native.indexOf('}else if(type=="followerSettings"){'));
  assert.match(equip, /if\(!ammo->IsBolt\(\)\)/);
  assert.doesNotMatch(equip, /Family\(/);
  assert.ok(equip.indexOf('ammo_queue_rules::Promote') < equip.indexOf('Close();'));
  assert.ok(equip.indexOf('ammo_queue::Suspend()') < equip.indexOf('RequestEquip(id)'));
  assert.doesNotMatch(equip, /ammo_queue::mode\s*=/);
  const preview = readFileSync(new URL('../src/arrows/useArrowBridge.ts', import.meta.url), 'utf8');
  assert.match(preview, /type === 'equip' && !arrow.bolt/);
  assert.doesNotMatch(preview, /arrow.family !== 'normal'/);
});

test('queue is priority-only while old version 2 saves remain readable', () => {
  const native = readFileSync(new URL('../../../magic-arrows/native/src/main.cpp', import.meta.url), 'utf8');
  const queue = readFileSync(new URL('../../../magic-arrows/native/src/ammo_queue.h', import.meta.url), 'utf8');
  const panel = readFileSync(new URL('../src/arrows/ArrowInventory.tsx', import.meta.url), 'utf8');
  assert.doesNotMatch(native, /QueueShotSink|queueShotSink|ammo_queue::mode|afterShot|queueMode/);
  assert.doesNotMatch(panel, /queueMode|循环箭矢|随机箭矢|arrow-mode-buttons/);
  assert.match(native, /version==1\|\|version==2/);
  assert.match(queue, /words\{0u,/);
  assert.match(queue, /order=std::move\(restored\);enabled=true;/);
  assert.match(native, /ammo_queue::order=std::move\(restored\);ammo_queue::enabled=true;/);
});

test('queued crafting gates the start button on the co-save and the per-spell ceiling', () => {
  const entry = { spell: 101, name: '火焰箭·火球术', label: '9995', total: 9995, remaining: 9995, progress: 1 };
  const orders = { available: true, limit: 10000, entries: [entry] };
  assert.equal(planCraft({ ...state, orders }, selection).error, ''); // 9995 + 5 reaches the ceiling exactly
  assert.match(planCraft({ ...state, orders: { ...orders, available: false } }, selection).error, /保存组件/);
  const nearlyFull = { ...orders, entries: [{ ...entry, label: '9998', total: 9998, remaining: 9998 }] };
  assert.match(planCraft({ ...state, orders: nearlyFull }, selection).error, /排队数量已达上限/);
  assert.equal(planCraft({ ...state, orders: nearlyFull }, { ...selection, bases: [{ id: 10, count: 2 }] }).error, '');
  const quote = readFileSync(new URL('../src/arrows/useCraftQuote.ts', import.meta.url), 'utf8');
  assert.match(quote, /craftType = normal \? 'normalCraft' : 'orderStart'/);
  assert.match(quote, /已加入制作队列/);
  const panel = readFileSync(new URL('../src/arrows/MagicCrafting.tsx', import.meta.url), 'utf8');
  assert.match(panel, /aria-label="制作队列"/);
});
