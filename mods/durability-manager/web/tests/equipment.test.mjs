import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';
import ts from 'typescript';

const source = readFileSync(new URL('../src/equipment.ts', import.meta.url), 'utf8');
const compiled = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.ESNext } }).outputText;
const { equippedFirst } = await import(`data:text/javascript;base64,${Buffer.from(compiled).toString('base64')}`);
const item = (id, equipped) => Object.freeze({ id, equipped, name: '钢剑' });

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
