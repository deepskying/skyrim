import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';
import ts from 'typescript';
const source = readFileSync(new URL('../src/refresh.ts', import.meta.url), 'utf8');
const compiled = ts.transpileModule(source, { compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ESNext } }).outputText;
const { createRefreshTransition, normalizeRefreshResult } = await import(`data:text/javascript;base64,${Buffer.from(compiled).toString('base64')}`);
const oldCards = [{ id: 'old', equipmentId: '1:1', type: 'weight' }];
const newCards = [{ id: 'new', equipmentId: '1:1', type: 'weight' }];
const receipt = { requestId: 'r1', equipmentId: '1:1', success: true, goldSpent: 80, message: '已支付' };
function harness() {
  let now = 0, sequence = 0;
  const timers = new Map(), saved = [], views = [], cleared = [];
  const controller = createRefreshTransition((view) => views.push(view), {
    now: () => now,
    set: (callback, delay) => { const id = sequence++; timers.set(id, { callback, at: now + delay }); saved.push(callback); return id; },
    clear: (id) => { cleared.push(id); timers.delete(id); },
  });
  const advance = (duration) => {
    const target = now + duration;
    for (;;) {
      const next = [...timers].filter(([, timer]) => timer.at <= target).sort((a, b) => a[1].at - b[1].at)[0];
      if (!next) break;
      now = next[1].at; timers.delete(next[0]); next[1].callback();
    }
    now = target;
  };
  return { controller, views, saved, cleared, advance };
}

test('malformed native refresh receipts are ignored', () => {
  for (const value of [null, [], {}, { ...receipt, requestId: '' }, { ...receipt, requestId: 'x'.repeat(129) },
    { ...receipt, success: 'true' }, { ...receipt, goldSpent: NaN }, { ...receipt, goldSpent: -1 }]) {
    assert.equal(normalizeRefreshResult(value), undefined);
  }
  assert.deepEqual(normalizeRefreshResult(receipt), receipt);
});

test('double clicks and unrelated updates cannot complete a pending refresh', () => {
  const h = harness();
  assert.equal(h.controller.start('r1', '1:1', oldCards), true);
  assert.equal(h.controller.start('r2', '1:1', oldCards), false);
  for (const value of [undefined, { ...receipt, requestId: 'old' }, { ...receipt, equipmentId: '1:2' }]) h.controller.receive(value, newCards);
  h.advance(1000);
  assert.equal(h.views.at(-1).phase, 'waiting');
  assert.deepEqual(h.views.at(-1).cards, oldCards);
});

test('fast successful replies wait for fade and reveal even identical card types', () => {
  const h = harness();
  h.controller.start('r1', '1:1', oldCards);
  h.controller.receive(receipt, newCards);
  h.controller.receive(receipt, []); // Duplicate must not restart or clear the animation.
  h.advance(139);
  assert.equal(h.views.at(-1).phase, 'waiting');
  h.advance(1);
  assert.equal(h.views.at(-1).phase, 'revealing');
  assert.deepEqual(h.views.at(-1).cards, newCards);
  assert.equal(h.views.at(-1).message, '已刷新 · 消耗 80 金币');
  assert.equal(h.controller.start('r2', '1:1', newCards), false);
  h.advance(400);
  assert.equal(h.views.at(-1).phase, 'idle');
  assert.equal(h.controller.isPending(), false);
});

test('native failure restores old cards and never displays success or charged cost', () => {
  const h = harness();
  h.controller.start('r1', '1:1', oldCards);
  h.controller.receive({ ...receipt, success: false, goldSpent: 0, message: '金币不足，本次未扣费' }, newCards);
  h.advance(10000);
  assert.deepEqual(h.views.at(-1).cards, oldCards);
  assert.equal(h.views.at(-1).phase, 'idle');
  assert.equal(h.views.at(-1).message, '金币不足，本次未扣费');
  assert.ok(h.views.every((view) => !view.message.includes('已刷新')));
});

test('timeout never retries or claims failure; a matching late reply still completes', () => {
  const h = harness();
  h.controller.start('r1', '1:1', oldCards);
  h.advance(10000);
  assert.equal(h.views.at(-1).phase, 'timeout');
  assert.equal(h.controller.start('r2', '1:1', oldCards), false);
  h.controller.receive({ ...receipt, goldSpent: 160 }, newCards);
  h.advance(400);
  assert.equal(h.views.at(-1).phase, 'idle');
  assert.equal(h.views.at(-1).message, '已刷新 · 消耗 160 金币');
});

test('unmount invalidates queued callbacks and old replies, including timer ID zero', () => {
  const h = harness();
  h.controller.start('r1', '1:1', oldCards);
  h.controller.receive(receipt, newCards);
  h.controller.dispose();
  const count = h.views.length;
  for (const callback of h.saved) callback();
  h.controller.receive(receipt, newCards);
  assert.equal(h.views.length, count);
  assert.ok(h.cleared.includes(0));
});

test('native refresh success is acknowledged after payment and storing the new draft', () => {
  const native = readFileSync(new URL('../../native/src/main.cpp', import.meta.url), 'utf8');
  const start = native.indexOf('void RefreshEnhancementCards(');
  const body = native.slice(start, native.indexOf('std::string SalvageDescription', start));
  assert.ok(body.indexOf('player->RemoveItem(gold') < body.indexOf('a_requestID, true, cost'));
  assert.ok(body.indexOf('g_enhancementDrafts.Store') < body.indexOf('a_requestID, true, cost'));
  assert.equal((body.match(/a_requestID, false, 0/g) ?? []).length, 5);
  assert.match(native, /request.value\("requestId", ""\)/);
});
