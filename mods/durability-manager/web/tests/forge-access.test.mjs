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
  assert.match(app, /无需锻造设施/);
  assert.doesNotMatch(app, /两分钟/);
});

test('only repair requires proximity; enhancement uses player readiness at all entry points', () => {
  const repair = native.indexOf('void RepairEquipment(');
  assert.match(native.slice(repair, repair + 650), /if \(!GetForgeContext\(\)\.active\)/);
  for (const name of ['SelectEquipmentForForge', 'RefreshEnhancementCards', 'ApplyEnhancementCard']) {
    const start = native.indexOf(`void ${name}(`);
    assert.ok(start >= 0, name);
    assert.match(native.slice(start, start + 650), /if \(!CanEnhanceEquipment\(\)\)/, name);
    assert.doesNotMatch(native.slice(start, start + 650), /GetForgeContext/, name);
  }
  assert.doesNotMatch(native, /if \(!result.active\) ClearForgeContext/);
  assert.match(native, /"cards", CanEnhanceEquipment\(\) \? EnhancementCardsJson/);
  assert.match(app, /enhancing && canEnhance/);
});
