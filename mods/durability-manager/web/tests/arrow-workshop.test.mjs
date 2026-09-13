import assert from 'node:assert/strict';
import test from 'node:test';
import { readFileSync } from 'node:fs';
import ts from 'typescript';
async function module(name) {
  const source = readFileSync(new URL(`../src/arrows/${name}.ts`, import.meta.url), 'utf8');
  const js = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.ESNext } }).outputText;
  return import(`data:text/javascript;base64,${Buffer.from(js).toString('base64')}`);
}
const { planCraft, matchingMaterials, moveQueue, matchesCraftReply } = await module('rules');
const { arrowDemo: state } = await module('demo');
const selection = { spell: 101, bases: [{ id: 10, count: 5 }], materials: [{ id: 201, count: 1 }] };
test('matching potions precede raw ingredients and unsupported families never charge', () => {
  const before = JSON.stringify(state.materials);
  assert.deepEqual(matchingMaterials(state.materials, state.spells[0]).map(m => m.id), [201, 202, 203]);
  assert.deepEqual(matchingMaterials(state.materials, state.spells[1]).map(m => m.id), [204]);
  assert.equal(JSON.stringify(state.materials), before);
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
