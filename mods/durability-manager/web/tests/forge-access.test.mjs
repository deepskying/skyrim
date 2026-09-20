import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';

const native = readFileSync(new URL('../../native/src/main.cpp', import.meta.url), 'utf8');
const app = readFileSync(new URL('../src/App.tsx', import.meta.url), 'utf8');

test('nearby access has no activation event or expiring unlock dependency', () => {
  assert.doesNotMatch(native, /TESActivateEvent|ActivateForgeContext|g_forgeActivatedAt|kForgeContextLifetime/);
  assert.match(native, /ForEachReferenceInRange\(player, workshop::kRadius/);
  assert.match(native, /station->IsDeleted\(\).*station->IsDisabled\(\).*station->Is3DLoaded\(\)/);
  assert.match(app, /附近无锻造设施/);
  assert.match(app, /强化和刷新需要靠近附魔台或锻造设备/);
  assert.doesNotMatch(app, /两分钟/);
});

test('enhancement mutations require stations while preview stays available', () => {
  const repair = native.indexOf('void RepairEquipment(');
  assert.match(native.slice(repair, repair + 650), /if \(!GetForgeContext\(\)\.active\)/);
  for (const name of ['RefreshEnhancementCards', 'ApplyEnhancementCard']) {
    const start = native.indexOf(`void ${name}(`);
    assert.ok(start >= 0, name);
    assert.match(native.slice(start, start + 650), /if \(!CanEnhanceEquipment\(\)\)/, name);
    assert.doesNotMatch(native.slice(start, start + 650), /GetForgeContext/, name);
  }
  assert.doesNotMatch(native, /if \(!result.active\) ClearForgeContext/);
  assert.match(native, /"cards", CanPreviewEnhancement\(\) \? EnhancementCardsJson/);
  assert.match(app, /enhancing \? <EnhancementPage/);
  const preview = native.indexOf('void SelectEquipmentForForge(');
  assert.match(native.slice(preview, preview + 300), /CanPreviewEnhancement/);
  const gate = native.indexOf('bool CanEnhanceEquipment()');
  assert.match(native.slice(gate, gate + 400), /stations.magic \|\| stations.normal/);
  const panel = readFileSync(new URL('../src/EnhancementPage.tsx', import.meta.url), 'utf8');
  assert.match(panel, /disabled=\{!available \|\| locked \|\| !cards.length/);
  assert.match(panel, /disabled=\{!available \|\| locked \|\| Boolean\(missingCost\(reviewed.materials\)\)/);
});
