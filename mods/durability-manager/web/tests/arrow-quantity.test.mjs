import assert from 'node:assert/strict';
import test from 'node:test';
import { readFileSync } from 'node:fs';
import ts from 'typescript';
function compiled(name) { return ts.transpileModule(readFileSync(new URL(`../src/arrows/${name}.ts`, import.meta.url), 'utf8'), { compilerOptions: { module: ts.ModuleKind.ESNext } }).outputText; }
const data = js => `data:text/javascript;base64,${Buffer.from(js).toString('base64')}`;
const rules = data(compiled('rules'));
const { clampQuantity, replaceStack, allocateBases, reconcileSelection, resourceSegments } = await import(data(compiled('quantity').replace("'./rules'", JSON.stringify(rules))));
const { arrowDemo: state } = await import(data(compiled('demo')));
test('quantity accepts zero and clamps to whole units and available stock', () => {
  assert.equal(clampQuantity(0, 20), 0); assert.equal(clampQuantity(-1, 20), 0);
  assert.equal(clampQuantity(3.9, 20), 3); assert.equal(clampQuantity(30, 20), 20);
  assert.equal(clampQuantity(NaN, 20), 0); assert.equal(clampQuantity(5, 0), 0);
  assert.deepEqual(replaceStack([{ id: 1, count: 2 }, { id: 2, count: 3 }], 1, 0), [{ id: 2, count: 3 }]);
});
test('inventory reconciliation clamps all bases to a combined 100 and removes depleted selections', () => {
  const s = { spell: 101, bases: [{ id: 10, count: 999 }, { id: 11, count: 99 }, { id: 12, count: 10 }], materials: [{ id: 201, count: 99 }, { id: 999, count: 1 }] };
  const result = reconcileSelection(state, s);
  assert.deepEqual(result.bases, [{ id: 10, count: 48 }, { id: 11, count: 52 }]);
  assert.deepEqual(result.materials, [{ id: 201, count: 4 }]);
  assert.equal(s.bases[0].count, 999);
});
test('changing spells keeps compatible bases and potions, removes incompatible charge', () => {
  const s = { spell: 103, bases: [{ id: 10, count: 5 }], materials: [{ id: 201, count: 1 }] };
  assert.deepEqual(reconcileSelection(state, s), s);
  assert.deepEqual(reconcileSelection(state, { ...s, spell: 102 }), { spell: 102, bases: s.bases, materials: [] });
  assert.deepEqual(reconcileSelection(state, { ...s, spell: 104 }), { spell: 104, bases: [], materials: [] });
});
test('partial output allocates actual base consumption in selected order', () => {
  const bases = [{ id: 10, count: 4 }, { id: 11, count: 4 }];
  assert.deepEqual(allocateBases(bases, 5), [{ id: 10, count: 4 }, { id: 11, count: 1 }]);
  assert.deepEqual(allocateBases(bases, 0), []);
});
test('resource meter splits remaining and spending without overflowing or dividing by zero', () => {
  const r = resourceSegments(220, 60);
  assert.equal(r.remaining, 160); assert.equal(r.shortage, 0);
  assert.equal(r.remainingPercent + r.spendingPercent, 100);
  const insufficient = resourceSegments(10, 25);
  assert.equal(insufficient.shortage, 15); assert.equal(insufficient.remainingPercent, 0); assert.equal(insufficient.spendingPercent, 100);
  assert.equal(resourceSegments(0, 25).spendingPercent, 0);
  assert.equal(resourceSegments(undefined, 25).known, false);
  assert.equal(resourceSegments(NaN, 25).known, false);
});
