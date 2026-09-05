import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';

const native = readFileSync(new URL('../../native/src/main.cpp', import.meta.url), 'utf8');
const app = readFileSync(new URL('../src/App.tsx', import.meta.url), 'utf8');

test('nearby access has no activation event or expiring unlock dependency', () => {
  assert.doesNotMatch(native, /TESActivateEvent|ActivateForgeContext|g_forgeActivatedAt|kForgeContextLifetime/);
  assert.match(native, /ForEachReferenceInRange\(player, workshop::kRadius/);
  assert.match(native, /station->IsDeleted\(\).*station->IsDisabled\(\).*station->Is3DLoaded\(\)/);
  assert.match(app, /附近无可用锻造设施/);
  assert.match(app, /无需先操作设施/);
  assert.doesNotMatch(app, /两分钟/);
});

test('repair, paid reroll and enhancement still revalidate native proximity before payment', () => {
  // Source-level contract guard, supplemented by the native distance/location tests.
  for (const name of ['RepairEquipment', 'RefreshEnhancementCards', 'ApplyEnhancementCard']) {
    const start = native.indexOf(`void ${name}(`);
    assert.ok(start >= 0, name);
    assert.match(native.slice(start, start + 650), /if \(!GetForgeContext\(\)\.active\)/, name);
  }
});
