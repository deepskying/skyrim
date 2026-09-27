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
  new Function('require', 'exports', compiled)(id => id === './SoulGemIcon' ? load('arrows/SoulGemIcon.tsx') : require(id), exports);
  return exports;
}
const { arrowDemo } = load('arrows/demo.ts');
const { SoulPoolPage } = load('arrows/SoulPool.tsx');
const markup = renderToStaticMarkup(createElement(SoulPoolPage, { state: arrowDemo, action: () => {}, active: true }));

test('the withdrawal card offers candidate gems, a slider and one action', () => {
  assert.match(markup, /role="radiogroup"/);
  assert.match(markup, /soul-gem-card/);
  assert.match(markup, /soul-gem-svg level-6/);
  assert.match(markup, /<svg/);
  assert.match(markup, /type="range"/);
  assert.match(markup, /兑换 1 颗/);
  assert.match(markup, /12 \/ 20/);
});

test('the deposit list still renders and the pool meter is bordered', () => {
  assert.match(markup, /存入灵魂石/);
  assert.match(markup, /soul-meter-fill/);
});

test('upgrade requirements are inline badges with a count', () => {
  assert.match(markup, /soul-requirement/);
  assert.match(markup, /×4/);
  assert.match(markup, /×1000/);
  assert.match(markup, /缺 1/);
});
