import assert from 'node:assert/strict';
import test from 'node:test';
import { readFileSync } from 'node:fs';
import ts from 'typescript';
const source = readFileSync(new URL('../src/equipment-selection.ts', import.meta.url), 'utf8');
const js = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.ESNext } }).outputText;
const { adjacentEquipment } = await import(`data:text/javascript;base64,${Buffer.from(js).toString('base64')}`);

test('keyboard navigation follows visible order and clamps at both edges', () => {
  assert.equal(adjacentEquipment(['c', 'b', 'a'], 'b', -1), 'c');
  assert.equal(adjacentEquipment(['c', 'b', 'a'], 'b', 1), 'a');
  assert.equal(adjacentEquipment(['c', 'b', 'a'], 'c', -1), 'c');
  assert.equal(adjacentEquipment(['c', 'b', 'a'], 'a', 1), 'a');
  assert.equal(adjacentEquipment(['b'], undefined, 1), 'b');
  assert.equal(adjacentEquipment([], undefined, -1), undefined);
});
