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

test('the withdrawal card offers candidate gems with their own inputs and one action', () => {
  assert.match(markup, /role="group"/);
  assert.match(markup, /soul-gem-card/);
  assert.match(markup, /soul-gem-svg/);
  assert.ok((markup.match(/<path/g) ?? []).length >= 12, 'every card draws both diamonds');
  assert.match(markup, /fill="none"/);
  assert.ok((markup.match(/type="number"/g) ?? []).length >= 6, 'every candidate gets its own input');
  assert.equal(markup.includes('type="range"'), false, 'the slider is gone');
  assert.match(markup, /请填写兑换数量/);
  assert.match(markup, /12 \/ 20/);
});

test('the deposit list still renders and the pool meter is bordered', () => {
  assert.match(markup, /存入灵魂石/);
  assert.match(markup, /soul-meter-fill/);
});

test('upgrade requirements are inline badges with a count, one set per plan', () => {
  assert.match(markup, /soul-plans/);
  assert.equal((markup.match(/class="soul-plan(?: ready)?"/g) ?? []).length, 2, 'the tier offers two plans');
  assert.match(markup, /方案甲/);
  assert.match(markup, /方案乙/);
  assert.match(markup, /soul-requirement/);
  assert.match(markup, /8\/4/);
  assert.match(markup, /1850\/1000/);
  assert.match(markup, /按方案乙扩容/, 'the affordable plan keeps its own confirm button');
  assert.match(markup, /材料或金币不足/, 'the plan that is short stays locked');
  assert.equal(markup.includes('缺 1'), false, 'the missing hint is gone');
});
