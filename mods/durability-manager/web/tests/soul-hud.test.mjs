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
  new Function('require', 'exports', compiled)(id => id === './soul-hud' ? load('soul-hud.ts') : require(id), exports);
  return exports;
}
const { normalizeSoulPoolHud } = load('soul-hud.ts');
const { SoulPoolHud } = load('SoulPoolHud.tsx');
const render = pool => renderToStaticMarkup(createElement(SoulPoolHud, { pool: normalizeSoulPoolHud(pool) }));

test('the soul pool HUD clamps points to the capacity', () => {
  assert.deepEqual(normalizeSoulPoolHud({ enabled: true, points: 12, capacity: 20, tier: 1 }), { enabled: true, points: 12, capacity: 20, tier: 1 });
  assert.deepEqual(normalizeSoulPoolHud({ enabled: true, points: 30, capacity: 20, tier: 1 }), { enabled: true, points: 20, capacity: 20, tier: 1 });
  assert.deepEqual(normalizeSoulPoolHud({ enabled: false, points: 5, capacity: 20, tier: 1 }), { enabled: false, points: 0, capacity: 0, tier: 0 });
  assert.equal(normalizeSoulPoolHud({ enabled: true, points: 1, capacity: 0, tier: 0 }), undefined);
  assert.equal(normalizeSoulPoolHud({ enabled: true, points: 'x', capacity: 20, tier: 0 }), undefined);
  assert.equal(normalizeSoulPoolHud(null), undefined);
});

test('the HUD strip prints the readout and hides a disabled pool', () => {
  const markup = render({ enabled: true, points: 7, capacity: 30, tier: 1 });
  assert.match(markup, /灵魂池/);
  assert.match(markup, /7 \/ 30/);
  assert.match(markup, /1 级上限/);
  assert.equal((markup.match(/soul-pool-segments/g) ?? []).length, 1);
  assert.equal((markup.match(/<i class="on">/g) ?? []).length, 2); // 7 / 30 rounds to two notches
  assert.equal(render({ enabled: false, points: 0, capacity: 0, tier: 0 }), '');
});
