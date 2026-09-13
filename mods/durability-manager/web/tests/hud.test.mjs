import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';
import ts from 'typescript';
import { runInNewContext } from 'node:vm';

const source = readFileSync(new URL('../src/hud.ts', import.meta.url), 'utf8');
const compiled = ts.transpileModule(source, { compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ESNext } }).outputText;
const { normalizeHudMessage, createHudReceiver, normalizeEquippedHud } = await import(`data:text/javascript;base64,${Buffer.from(compiled).toString('base64')}`);
const normal = { id: 10, kind: 'weapon', title: '钢弓', detail: '耐久', durationMilliseconds: 1500, current: 50, maximum: 100 };

test('native HUD readiness probe recovers when page mounts before bridge injection', () => {
  const header = readFileSync(new URL('../../native/src/hud_bridge.h', import.meta.url), 'utf8');
  const probe = header.match(/R"JS\(([\s\S]*?)\)JS"/)[1];
  const window = {};
  const sent = [];
  runInNewContext(probe, { window }); // Page is not mounted yet.
  window.DurabilityManager = {
    updateEquippedHud() {},
    reportReady() { window.durabilityManagerAction?.('ready'); },
  };
  window.DurabilityManager.reportReady(); // Original one-shot ready is lost.
  runInNewContext(probe, { window }); // Native listener still unavailable.
  assert.deepEqual(sent, []);
  window.durabilityManagerAction = value => sent.push(value);
  runInNewContext(probe, { window });
  assert.deepEqual(sent, ['ready']);
  delete window.DurabilityManager;
  runInNewContext(probe, { window }); // Navigation/reload remains safe.
  assert.deepEqual(sent, ['ready']);
});

test('persistent snapshots distinguish copies, reject malformed rows, and clear on unequip', () => {
  const right = { id: '100:1', kind: 'weapon', title: '钢剑', detail: '右手', current: 80, maximum: 100 };
  const left = { ...right, id: '100:2', detail: '左手', current: 20 };
  assert.deepEqual(normalizeEquippedHud([right, left, right, null, { ...left, id: 'bad', maximum: 0 }]), [right, left]);
  assert.deepEqual(normalizeEquippedHud([left]), [left]);
  assert.deepEqual(normalizeEquippedHud([]), []);
  assert.equal(normalizeEquippedHud(null), undefined);
  assert.equal(normalizeEquippedHud([{ ...right, current: -3 }])[0].current, 0);
  assert.equal(normalizeEquippedHud([{ ...right, current: 1000 }])[0].current, 100);
});

test('clearing HUD during a menu or load invalidates callbacks and allows new notifications', () => {
  const h = harness();
  h.receiver.receive(normal);
  h.receiver.clear();
  h.callbacks[0]();
  assert.equal(h.shown.at(-1), undefined);
  assert.deepEqual(h.hidden, []);
  h.receiver.receive({ ...normal, id: 11 });
  h.callbacks[0]();
  assert.equal(h.shown.at(-1).id, 11);
  h.callbacks[1]();
  assert.deepEqual(h.hidden, [11]);
});

test('HUD rejects null, malformed IDs and unknown kinds without throwing', () => {
  for (const value of [null, undefined, [], 'oops', 3, {}, { ...normal, id: null }, { ...normal, id: NaN },
    { ...normal, id: Infinity }, { ...normal, id: -1 }, { ...normal, id: 1.2 }, { ...normal, id: 0x100000000 }, { ...normal, kind: {} }]) {
    assert.equal(normalizeHudMessage(value), undefined);
  }
  assert.deepEqual(normalizeHudMessage(normal), normal);
  assert.equal(normalizeHudMessage({ ...normal, id: 0 }).id, 0); // Native uint32 wrap.
});

test('HUD sanitizes text, bounds duration, and omits invalid progress bars', () => {
  const sanitized = normalizeHudMessage({ ...normal, title: {}, detail: null, durationMilliseconds: null });
  assert.equal(sanitized.title, '装备耐久');
  assert.equal(sanitized.detail, '');
  assert.equal(sanitized.durationMilliseconds, 3000);
  for (const [durationMilliseconds, expected] of [[-1, 500], [1e12, 10000], [NaN, 3000], [Infinity, 3000], [750, 750]]) {
    assert.equal(normalizeHudMessage({ ...normal, durationMilliseconds }).durationMilliseconds, expected);
  }
  for (const fields of [{ current: null }, { current: Infinity }, { maximum: 0 }, { maximum: -1 }, { maximum: NaN }]) {
    const result = normalizeHudMessage({ ...normal, ...fields });
    assert.equal(result.current, undefined);
    assert.equal(result.maximum, undefined);
  }
  assert.equal(normalizeHudMessage({ ...normal, current: -5 }).current, 0);
  assert.equal(normalizeHudMessage({ ...normal, current: 200 }).current, 100);
  assert.equal(normalizeHudMessage({ id: 11, kind: 'warning', title: '低耐久', detail: '请修复', durationMilliseconds: 3000 }).maximum, undefined);
});

function harness() {
  const shown = [], hidden = [], callbacks = [], cleared = [], delays = [];
  const receiver = createHudReceiver((message) => shown.push(message), (id) => hidden.push(id), {
    set: (callback, delay) => { callbacks.push(callback); delays.push(delay); return callbacks.length - 1; },
    clear: (id) => cleared.push(id),
  });
  return { receiver, shown, hidden, callbacks, cleared, delays };
}

test('actual HUD receiver ignores null without cancelling the current notification', () => {
  const h = harness();
  assert.doesNotThrow(() => h.receiver.receive(null));
  assert.equal(h.callbacks.length, 0);
  h.receiver.receive(normal);
  h.receiver.receive(null);
  h.receiver.receive({});
  assert.deepEqual(h.shown, [normal]);
  assert.deepEqual(h.cleared, []);
  assert.deepEqual(h.delays, [1500]);
  h.callbacks[0]();
  assert.equal(h.shown.at(-1), undefined);
  assert.deepEqual(h.hidden, [10]);
});

test('replacement and unmount invalidate old timers, including timer ID zero', () => {
  const h = harness();
  h.receiver.receive(normal);
  h.receiver.receive({ ...normal, id: 11 });
  assert.deepEqual(h.cleared, [0]);
  h.callbacks[0](); // A queued callback from the previous message must not hide the new HUD.
  assert.equal(h.shown.at(-1).id, 11);
  assert.deepEqual(h.hidden, []);
  h.receiver.dispose();
  h.callbacks[1]();
  h.receiver.receive({ ...normal, id: 12 });
  assert.deepEqual(h.cleared, [0, 1]);
  assert.deepEqual(h.hidden, []);
  assert.equal(h.shown.length, 2);
});

test('native regression guard: panel and refresh bypass unsafe default-object gold lookup', () => {
  // This guards the known crash path; it is not a substitute for an in-game engine test.
  const native = readFileSync(new URL('../../native/src/main.cpp', import.meta.url), 'utf8');
  assert.doesNotMatch(native, /->\s*GetGoldAmount\s*\(/);
  assert.match(native, /LookupByID<RE::TESObjectMISC>\(0x0000000FU\)/);
  assert.match(native, /a_player->GetItemCount\(gold\)/);
  assert.match(native, /\{ "gold", PlayerGoldCount\(player\) \}/);
  assert.match(native, /PlayerGoldCount\(player\) < static_cast<std::int32_t>\(cost\)/);
});
