import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import { test } from 'node:test';
import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import ts from 'typescript';

function load(name) {
  const source = readFileSync(new URL(`../src/${name}`, import.meta.url), 'utf8');
  const compiled = ts.transpileModule(source, { compilerOptions: { target: ts.ScriptTarget.ES2022, jsx: ts.JsxEmit.ReactJSX, module: ts.ModuleKind.CommonJS } }).outputText;
  const exports = {};
  const require = createRequire(import.meta.url);
  // The component imports its rules module by path; hand it the freshly compiled one.
  new Function('require', 'exports', compiled)(id => id === './craft-hud' ? load('craft-hud.ts') : require(id), exports);
  return exports;
}
const { normalizeCraftOrders, craftOrderHudLimit } = load('craft-hud.ts');
const { CraftOrderHud } = load('CraftOrderHud.tsx');
const sample = { spell: 21, name: '奥术箭·火球术', label: '12', total: 12, remaining: 12, family: 'fire' };
const render = (orders, viewportHeight = 1080) => {
  const previous = globalThis.window;
  globalThis.window = { innerHeight: viewportHeight };
  try {
    return renderToStaticMarkup(createElement(CraftOrderHud, { orders: normalizeCraftOrders(orders) }));
  } finally {
    globalThis.window = previous;
  }
};

test('craft order snapshot drops batches that cannot describe a ring', () => {
  for (const input of [null, undefined, [], 'oops', 3, {}, { entries: 'x' }]) assert.equal(normalizeCraftOrders(input), undefined);
  const snapshot = normalizeCraftOrders({ paused: 'yes', reason: 5, entries: [
    sample, { ...sample }, { ...sample, spell: 22, total: 0 }, { ...sample, spell: 23, remaining: -1 },
    { ...sample, spell: 24, total: 4, remaining: 5 }, { ...sample, spell: 25, name: '', label: '', family: 'wood', total: 5, remaining: 5 },
    null, { ...sample, spell: 26, label: '1.5K', family: 'ice', total: 4500, remaining: 1500 },
  ] });
  assert.deepEqual(snapshot.entries.map(entry => entry.spell), [21, 25, 26]);
  assert.equal(snapshot.paused, false);
  assert.equal(snapshot.reason, '');
  assert.equal(snapshot.entries[0].progress, 1);
  assert.equal(snapshot.entries[1].family, 'arcane');
  assert.equal(snapshot.entries[1].name, '魔法箭');
  assert.equal(snapshot.entries[1].label, '5');
  assert.equal(snapshot.entries[2].progress, 1500 / 4500);
  assert.deepEqual(normalizeCraftOrders({ entries: [] }).entries, []);
});

test('each diamond traces the arrows still to craft inside a family tint', () => {
  const markup = render({ entries: [sample, { ...sample, spell: 26, name: '奥术箭·冰锥术', label: '1.5K', family: 'ice', total: 4500, remaining: 1500 }] });
  assert.match(markup, /class="fire"/);
  assert.match(markup, /class="ice"/);
  assert.match(markup, /stroke-dasharray="100 100"/);
  assert.match(markup, /stroke-dasharray="33.3 100"/);
  assert.match(markup, />12</);
  assert.match(markup, />1.5K</);
  assert.match(markup, /2 种法术/);
  assert.doesNotMatch(markup, /craft-order-hud paused/);
  assert.doesNotMatch(markup, /NaN|Infinity/);
});

test('paused queues keep the diamonds and name the reason', () => {
  const markup = render({ paused: true, reason: '战斗中暂停', entries: [sample] });
  assert.match(markup, /class="craft-order-hud paused"/);
  assert.match(markup, /战斗中暂停/);
  const unavailable = render({ paused: true, entries: [sample] });
  assert.match(unavailable, /已暂停/);
});

test('empty queues render nothing and long queues report the hidden spells', () => {
  assert.equal(render({ entries: [] }), '');
  assert.equal(render(undefined), '');
  const entries = Array.from({ length: 9 }, (_, index) => ({ ...sample, spell: 100 + index, name: `奥术箭·${index}` }));
  const markup = render({ entries }, 720);
  assert.equal((markup.match(/class="order-square"/g) ?? []).length, craftOrderHudLimit(720));
  assert.match(markup, /另有 5 种法术排队/);
  assert.match(markup, />\+5</);
  assert.deepEqual([craftOrderHudLimit(0), craftOrderHudLimit(NaN), craftOrderHudLimit(760), craftOrderHudLimit(900), craftOrderHudLimit(1440)], [8, 8, 4, 6, 8]);
});

test('native and panel wiring push the crafting queue into the equipment HUD', () => {
  const native = readFileSync(new URL('../../native/src/main.cpp', import.meta.url), 'utf8');
  assert.match(native, /window\.DurabilityManager\?\.updateCraftOrders\?\.\(/);
  assert.match(native, /unified_workshop::CraftOrderJson\(\)/);
  const bridge = readFileSync(new URL('../../../workshop/native/src/workshop_bridge.h', import.meta.url), 'utf8');
  assert.match(bridge, /std::string CraftOrderJson\(\)/);
  const arrows = readFileSync(new URL('../../../magic-arrows/native/src/main.cpp', import.meta.url), 'utf8');
  assert.match(arrows, /std::string unified_workshop::CraftOrderJson\(\)\{return craft_order::State\(\)\.dump\(\);\}/);
  const app = readFileSync(new URL('../src/App.tsx', import.meta.url), 'utf8');
  assert.match(app, /updateCraftOrders: value =>/);
  assert.match(app, /<CraftOrderHud orders=\{craftOrders\} \/>/);
});
