import assert from 'node:assert/strict';
import test from 'node:test';
import { readFileSync } from 'node:fs';
import ts from 'typescript';
const source = readFileSync(new URL('../src/recycling-hotkey.ts', import.meta.url), 'utf8');
const js = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.ESNext } }).outputText;
const { createRecyclingCapture, recyclingKeyCode, recyclingKeyLabel } = await import(`data:text/javascript;base64,${Buffer.from(js).toString('base64')}`);
test('standalone right Alt records on release and remains distinct from left Alt', () => {
  const capture = createRecyclingCapture();
  assert.equal(capture('AltRight', true), undefined);
  assert.deepEqual(capture('AltRight', false), { keyCode: 184, safetyCode: 184 });
  assert.equal(recyclingKeyLabel(184), '右 Alt');
  assert.equal(recyclingKeyCode('AltLeft'), 56);
});
test('single key clears the old safety chord, combo uses the actual side', () => {
  assert.deepEqual(createRecyclingCapture()('KeyD', true), { keyCode: 32, safetyCode: 32 });
  const capture = createRecyclingCapture();
  capture('ControlRight', true);
  assert.deepEqual(capture('Delete', true), { keyCode: 211, safetyCode: 157 });
});
test('unsupported keys and multiple modifiers cannot silently become another binding', () => {
  const capture = createRecyclingCapture();
  assert.equal(capture('Enter', true), 'invalid');
  assert.deepEqual(capture('F12', true), { keyCode: 88, safetyCode: 88 });
  capture('ShiftLeft', true); capture('AltRight', true);
  assert.equal(capture('KeyD', true), 'invalid');
  assert.equal(capture('AltRight', false), undefined);
  assert.equal(capture('ShiftLeft', false), 'invalid');
  assert.deepEqual(capture('Space', true), { keyCode: 57, safetyCode: 57 });
});
test('native setter persists its own config without Papyrus or MCM', () => {
  const native = readFileSync(new URL('../../native/src/main.cpp', import.meta.url), 'utf8');
  const service = readFileSync(new URL('../../native/src/inventory_recycling.inl', import.meta.url), 'utf8');
  assert.doesNotMatch(native, /zsrMCM|WorkshopSetRecycleKey|DispatchMethodCall/);
  assert.match(native, /if \(!WriteRecyclingSettings\(settings\)\)/);
  assert.match(service, /EquipmentWorkshop.recycling.json/);
  assert.match(service, /MOVEFILE_REPLACE_EXISTING/);
  assert.match(service, /before - after != amount/);
  assert.match(service, /\*selected != expected/);
});
test('recycling materials resolve concrete records through As, not an exact None form-type lookup', () => {
  const service = readFileSync(new URL('../../native/src/inventory_recycling.inl', import.meta.url), 'utf8');
  const resolver = service.slice(service.indexOf('RE::TESBoundObject* RecyclingForm('), service.indexOf('std::map<RE::TESBoundObject*, std::int32_t> RecyclingMaterials('));
  assert.doesNotMatch(resolver, /LookupForm<RE::TESBoundObject>/);
  assert.match(resolver, /data->LookupForm\(id,/);
  assert.match(resolver, /form->As<RE::TESBoundObject>\(\)/);
});
test('native recycling leaves successful reward feedback to the item pickup UI', () => {
  const native = readFileSync(new URL('../../native/src/main.cpp', import.meta.url), 'utf8');
  const service = readFileSync(new URL('../../native/src/inventory_recycling.inl', import.meta.url), 'utf8');
  assert.doesNotMatch(native, /NotifySalvagePickups/);
  assert.doesNotMatch(service, /已回收「/);
  assert.match(service, /if \(!removed\) RE::DebugNotification/);
});
