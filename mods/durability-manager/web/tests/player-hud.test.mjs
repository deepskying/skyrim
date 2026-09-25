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
  new Function('require', 'exports', compiled)(createRequire(import.meta.url), exports);
  return exports;
}
const { normalizePlayerHud } = load('player-hud.ts');
const { PlayerHud } = load('PlayerHud.tsx');
const sample = { level: 21, experience: 321, experienceNext: 600, fire: -25, frost: 50, shock: 0, magic: 25,
  poison: 0, disease: 0, armor: 1875, speed: 100, gold: 44735, weight: 851, carryWeight: 800, gameMinutes: 953 };
const render = (overrides = {}) => renderToStaticMarkup(createElement(PlayerHud, { state: normalizePlayerHud({ ...sample, ...overrides }) }));

test('player snapshot rejects malformed records and preserves resistance vulnerabilities', () => {
  for (const input of [null, [], {}, { level: NaN }, { level: 0 }]) assert.equal(normalizePlayerHud(input), undefined);
  assert.equal(normalizePlayerHud(sample).fire, -25);
  const state = normalizePlayerHud({ ...sample, gold: Infinity, experienceNext: NaN, speed: '100', gameMinutes: 1441 });
  assert.equal(state.gold, null);
  assert.equal(state.experienceNext, null);
  assert.equal(state.speed, null);
  assert.equal(state.gameMinutes, 1);
});

test('diamond traces level experience clockwise and clamps pending level-up overflow', () => {
  assert.match(render(), /stroke-dasharray="53.5 100"/);
  assert.match(render({ experience: 900 }), /stroke-dasharray="100 100"/);
  assert.match(render({ experience: 0 }), /stroke-dasharray="0 100"/);
  assert.match(render({ experienceNext: 0 }), /stroke-dasharray="0 100"/);
  const unavailable = render({ experience: null, experienceNext: null });
  assert.match(unavailable, /— \/ —/);
  assert.doesNotMatch(unavailable, /NaN|Infinity/);
});

test('utility row distinguishes overburden from capacity and renders game midnight', () => {
  assert.match(render(), /player-stat overloaded/);
  assert.doesNotMatch(render({ weight: 800 }), /player-stat overloaded/);
  assert.match(render(), /15:53/);
  assert.match(render({ gameMinutes: 0 }), /00:00/);
  assert.match(render(), /44,735/);
});

test('readouts keep resistances above speed, armor, time, weight and gold', () => {
  const markup = render();
  const labels = ['疾病抗性', '移动速度', '护甲值', '游戏时间', '负重', '金币'];
  const positions = labels.map(label => markup.indexOf(`aria-label="${label} `));
  assert.ok(positions.every(position => position >= 0));
  assert.deepEqual(positions, [...positions].sort((a, b) => a - b));
});
