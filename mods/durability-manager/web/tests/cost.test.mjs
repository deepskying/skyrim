import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';
import ts from 'typescript';
const source = readFileSync(new URL('../src/cost.ts', import.meta.url), 'utf8');
const compiled = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.ESNext } }).outputText;
const { costLabel, missingCost } = await import(`data:text/javascript;base64,${Buffer.from(compiled).toString('base64')}`);
const gold = { name: 'Septims', required: 200, owned: 100, isGold: true };
const iron = { name: '金币色铁锭', required: 2, owned: 10, isGold: false };

test('cost labels use the native gold flag, never the localized name', () => {
  assert.equal(costLabel([iron]), '仅材料');
  assert.equal(costLabel([gold]), '200 金币');
  assert.equal(costLabel([gold, iron]), '200 金币 + 材料');
  assert.equal(costLabel([gold, { ...gold, required: 80 }]), '280 金币');
  assert.equal(costLabel([{ ...gold, isGold: undefined }]), '费用见材料清单');
  assert.equal(costLabel([]), '费用见材料清单');
  assert.equal(costLabel([{ ...gold, required: NaN }]), '费用见材料清单');
});

test('affordability distinguishes missing gold from missing crafting materials', () => {
  assert.equal(missingCost([gold, iron]), '金币不足');
  assert.equal(missingCost([{ ...gold, owned: 200 }, { ...iron, owned: 0 }]), '材料不足');
  assert.equal(missingCost([{ ...gold, owned: 200 }, iron]), undefined);
});

test('native material lists identify the exact gold record and buttons show actual cost', () => {
  const native = readFileSync(new URL('../../native/src/main.cpp', import.meta.url), 'utf8');
  assert.match(native, /"isGold", material && material->GetFormID\(\) == 0xFU/);
  assert.match(native, /"isGold", requirement.formID == 0xFU/);
  const app = readFileSync(new URL('../src/App.tsx', import.meta.url), 'utf8');
  const page = readFileSync(new URL('../src/EnhancementPage.tsx', import.meta.url), 'utf8');
  assert.match(app, /costLabel\(selected.repairMaterials\)/);
  assert.match(page, /costLabel\(card.materials\)/);
  assert.match(page, /costLabel\(reviewed.materials\)/);
});
