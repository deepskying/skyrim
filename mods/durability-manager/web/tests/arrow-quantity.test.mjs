import assert from 'node:assert/strict';
import test from 'node:test';
import { readFileSync } from 'node:fs';
import ts from 'typescript';
function compiled(name) { return ts.transpileModule(readFileSync(new URL(`../src/arrows/${name}.ts`, import.meta.url), 'utf8'), { compilerOptions: { module: ts.ModuleKind.ESNext } }).outputText; }
const data = js => `data:text/javascript;base64,${Buffer.from(js).toString('base64')}`;
const rules = data(compiled('rules'));
const { clampQuantity, replaceStack, allocateBases, reconcileSelection, resourceSegments, fillCharge } = await import(data(compiled('quantity').replace("'./rules'", JSON.stringify(rules))));
const { arrowDemo: state } = await import(data(compiled('demo')));
test('quantity accepts zero and clamps to whole units and available stock', () => {
  assert.equal(clampQuantity(0, 20), 0); assert.equal(clampQuantity(-1, 20), 0);
  assert.equal(clampQuantity(3.9, 20), 3); assert.equal(clampQuantity(30, 20), 20);
  assert.equal(clampQuantity(NaN, 20), 0); assert.equal(clampQuantity(5, 0), 0);
  assert.deepEqual(replaceStack([{ id: 1, count: 2 }, { id: 2, count: 3 }], 1, 0), [{ id: 2, count: 3 }]);
});
test('inventory reconciliation clamps to stock, one box of 999 and one batch of 10000', () => {
  const s = { spell: 101, bases: [{ id: 10, count: 999 }, { id: 11, count: 99 }, { id: 12, count: 10 }], materials: [{ id: 201, count: 99 }, { id: 999, count: 1 }] };
  const result = reconcileSelection(state, s);
  assert.deepEqual(result.bases, [{ id: 10, count: 48 }, { id: 11, count: 60 }, { id: 12, count: 10 }]);
  assert.deepEqual(result.materials, [{ id: 201, count: 4 }]);
  assert.equal(s.bases[0].count, 999);
  const stocked = { ...state, arrows: Array.from({ length: 12 }, (_, i) => ({ id: 20 + i, name: `箭${i}`, family: 'normal', count: 20000, runtimeBase: true, fireballBase: true })) };
  // A single box stops at 999 even with 20000 in stock.
  assert.deepEqual(reconcileSelection(stocked, { spell: 101, bases: [{ id: 20, count: 5000 }], materials: [] }).bases, [{ id: 20, count: 999 }]);
  // Eleven full boxes would pass 10000 arrows, so the last surviving stack is trimmed.
  const batch = reconcileSelection(stocked, { spell: 101, bases: Array.from({ length: 12 }, (_, i) => ({ id: 20 + i, count: 999 })), materials: [] });
  assert.equal(batch.bases.reduce((n, b) => n + b.count, 0), 10000);
  assert.equal(batch.bases.length, 11);
  assert.deepEqual(batch.bases[10], { id: 30, count: 10 });
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

test('fill charge prefers potions, adds only the shortage, and is idempotent', () => {
  const selection = { spell: 101, bases: [{ id: 10, count: 12 }], materials: [{ id: 203, count: 1 }] };
  const before = structuredClone(selection);
  const result = fillCharge(state, selection);
  assert.deepEqual(result.materials, [{ id: 203, count: 1 }, { id: 201, count: 3 }]);
  assert.deepEqual(fillCharge(state, result), result);
  assert.deepEqual(selection, before);
});
test('fill charge uses compatible stock only and cannot exceed native stack limits', () => {
  const inventory = structuredClone(state);
  inventory.materials = [{ id: 201, name: 'Small potion', kind: 'potion', count: 1, charges: { fire: 10 } },
    { id: 202, name: 'Ice potion', kind: 'potion', count: 100, charges: { ice: 100 } },
    { id: 203, name: 'Ingredient', kind: 'ingredient', count: 2, charges: { fire: 5 } }];
  const result = fillCharge(inventory, { spell: 101, bases: [{ id: 10, count: 10 }], materials: [] });
  assert.deepEqual(result.materials, [{ id: 201, count: 1 }, { id: 203, count: 2 }]);
  assert.deepEqual(fillCharge(inventory, { spell: 101, bases: [], materials: [] }).materials, []);
  assert.deepEqual(fillCharge(inventory, { spell: 104, bases: [{ id: 10, count: 5 }], materials: [] }).materials, []);
});
test('prepared-only fill spends potions and poisons but never raw ingredients', () => {
  const inventory = structuredClone(state);
  inventory.materials = [{ id: 201, name: 'Small potion', kind: 'potion', count: 1, charges: { fire: 10 } },
    { id: 202, name: 'Big poison', kind: 'poison', count: 1, charges: { fire: 100 } },
    { id: 203, name: 'Ingredient', kind: 'ingredient', count: 20, charges: { fire: 100 } }];
  const selection = { spell: 101, bases: [{ id: 10, count: 12 }], materials: [] };
  const before = structuredClone(selection);
  // Potion then poison cover 110 of the 120 charge; the prepared-only filler stops there
  // instead of reaching for the ingredient the normal filler would use.
  assert.deepEqual(fillCharge(inventory, selection, true).materials, [{ id: 201, count: 1 }, { id: 202, count: 1 }]);
  assert.deepEqual(fillCharge(inventory, selection).materials, [{ id: 201, count: 1 }, { id: 202, count: 1 }, { id: 203, count: 1 }]);
  assert.deepEqual(selection, before);
});
