import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';
import ts from 'typescript';

// Transpile the actual pure bridge helpers; no browser or additional test dependency required.
const source = readFileSync(new URL('../src/enhancement.ts', import.meta.url), 'utf8');
const compiled = ts.transpileModule(source, { compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ESNext } }).outputText;
const { normalizeCards, confirmationKey, failureDescription } = await import(`data:text/javascript;base64,${Buffer.from(compiled).toString('base64')}`);
const card = {
  id: 'draft-1', equipmentId: '1:32768', type: 'weight', tier: '标准', title: '轻量重构', description: '下限 0.1', value: '重量 -1',
  preview: [{ label: '重量', before: '0.5', after: '0.1' }], successChance: 88, materials: [{ name: '铁锭', required: 2, owned: 4 }],
};

test('null and malformed state cannot create selectable cards', () => {
  for (const input of [null, undefined, {}, 'oops', [null, 2, {}, { ...card, type: '__proto__' }, { ...card, equipmentId: null }]]) {
    assert.deepEqual(normalizeCards(input), []);
  }
  for (const override of [{ preview: null }, { preview: [null] }, { materials: null }, { materials: [null] },
    { materials: [{ name: '铁锭', owned: 4, required: NaN }] }, { successChance: NaN }, { successChance: 101 }]) {
    assert.ok(normalizeCards([{ ...card, ...override }])[0].blockedReason);
  }
});
test('preserves native preview and instance ID; rejects duplicates and marks missing costs', () => {
  const result = normalizeCards([card, card]);
  assert.equal(result.length, 1);
  assert.equal(result[0].equipmentId, card.equipmentId);
  assert.deepEqual(result[0].preview, card.preview);
  assert.equal(result[0].blockedReason, undefined);
  assert.equal(normalizeCards([{ ...card, materials: [{ name: '铁锭', owned: 1, required: 2 }] }])[0].blockedReason, '材料不足');
  assert.equal(normalizeCards([{ ...card, blockedReason: '请先卸下装备' }])[0].blockedReason, '请先卸下装备');
});
test('changed offer, costs, instance, durability or protection invalidate confirmation', () => {
  const item = { id: '1:32768', enhancementLevel: 4, current: 50, quest: false, unique: false };
  const original = confirmationKey(item, card);
  assert.equal(original, confirmationKey({ ...item }, { ...card }));
  for (const updated of [{ ...item, id: '2:32768' }, { ...item, current: 49 }, { ...item, quest: true }, { ...item, enhancementLevel: 5 }]) {
    assert.notEqual(original, confirmationKey(updated, card));
  }
  for (const updated of [{ ...card, id: 'draft-2' }, { ...card, successChance: 80 }, { ...card, materials: [] }]) {
    assert.notEqual(original, confirmationKey(item, updated));
  }
});
test('risk copy distinguishes destruction, protected downgrade and level zero', () => {
  assert.match(failureDescription({ quest: false, unique: false, enhancementLevel: 4 }), /失败会分解/);
  assert.match(failureDescription({ quest: true, unique: false, enhancementLevel: 4 }), /降至 \+3/);
  assert.match(failureDescription({ quest: false, unique: true, enhancementLevel: 0 }), /降至 \+0/);
});

test('review has no acknowledgement gate but retains risks, cost and duplicate-submit guards', () => {
  const page = readFileSync(new URL('../src/EnhancementPage.tsx', import.meta.url), 'utf8');
  assert.doesNotMatch(page, /acknowledged|setAcknowledged|risk-acknowledgement|我已了解|type="checkbox"/);
  assert.match(page, /className="enhancement-risk"/);
  assert.match(page, /failureDescription\(item\)/);
  assert.match(page, /className="confirm-enhancement" disabled=\{locked \|\| Boolean\(missingCost\(reviewed.materials\)\)\}/);
  assert.match(page, /if \(reviewed && !locked && !missingCost\(reviewed.materials\)\) dispatch\('applyEnhancement'/);
  assert.match(page, /if \(submitted.current \|\| transition.isPending\(\)\) return/);
  assert.match(page, /confirmationKey\(item, offer\) === review\?\.key/);
  assert.match(page, /取消，返回卡片/);
});
