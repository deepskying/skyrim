import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';
import ts from 'typescript';

const source = readFileSync(new URL('../src/equipment.ts', import.meta.url), 'utf8');
const compiled = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.ESNext } }).outputText;
const { equippedFirst, maintenanceOrder } = await import(`data:text/javascript;base64,${Buffer.from(compiled).toString('base64')}`);
const item = (id, equipped) => Object.freeze({ id, equipped, name: '钢剑' });

test('maintenance prioritizes equipped, then percentage, with stable ties and immutable input', () => {
  const gear = (id, equipped, current, maximum) => Object.freeze({ id, equipped, current, maximum });
  const input = Object.freeze([
    gear('full', false, 50, 50), gear('worn-full', true, 100, 100),
    gear('low', false, 60, 200), gear('broken', false, 0, 85),
    gear('worn-low', true, 1, 100), gear('equal', false, 30, 100),
  ]);
  const sorted = maintenanceOrder(input);
  assert.deepEqual(sorted.map(x => x.id), ['worn-full', 'worn-low', 'broken', 'low', 'equal', 'full']);
  assert.deepEqual(input.map(x => x.id), ['full', 'worn-full', 'low', 'broken', 'worn-low', 'equal']);
  assert.equal(sorted[3], input[2]);
  assert.deepEqual(maintenanceOrder([]), []);
  const repaired = input.map(x => x.id === 'broken' ? { ...x, current: 85 } : x);
  assert.deepEqual(maintenanceOrder(repaired).map(x => x.id), ['worn-full', 'worn-low', 'low', 'equal', 'full', 'broken']);
});

test('equipped instances come first with stable group order and no input mutation', () => {
  const input = Object.freeze([item('1:1', false), item('1:2', true), item('1:3', false), item('1:4', true)]);
  const sorted = equippedFirst(input);
  assert.deepEqual(sorted.map((value) => value.id), ['1:2', '1:4', '1:1', '1:3']);
  assert.deepEqual(input.map((value) => value.id), ['1:1', '1:2', '1:3', '1:4']);
  assert.equal(sorted[0], input[1]);
  assert.equal(sorted.find((value) => value.id === '1:3'), input[2]);
});

test('empty and single-group lists preserve order; new equip state changes priority', () => {
  assert.deepEqual(equippedFirst([]), []);
  for (const equipped of [true, false]) {
    const input = [item('a', equipped), item('b', equipped)];
    assert.deepEqual(equippedFirst(input), input);
  }
  assert.deepEqual(equippedFirst([item('a', false), item('b', true)]).map((value) => value.id), ['b', 'a']);
  assert.deepEqual(equippedFirst([item('a', true), item('b', false)]).map((value) => value.id), ['a', 'b']);
});

test('panel sorts the merged list and continues to select by instance ID', () => {
  // Source-level guard for integration with inventory/repair deduplication.
  const app = readFileSync(new URL('../src/App.tsx', import.meta.url), 'utf8');
  assert.match(app, /return equippedFirst\(\[\.\.\.state.equipped, \.\.\.state.repairQueue.filter/);
  assert.match(app, /filteredEquipment.find\(\(item\) => item.id === selectedId\)/);
});
