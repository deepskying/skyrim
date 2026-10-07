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
  new Function('require', 'exports', compiled)(id => id === './SoulGemIcon' ? load('arrows/SoulGemIcon.tsx') : id === './divine-demo' ? load('arrows/divine-demo.ts') : require(id), exports);
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
  assert.match(markup, /soul-meter-segments/);
});

test('an unrolled pool explains itself instead of showing a dead button', () => {
  const blank = { ...arrowDemo, soulPool: { ...arrowDemo.soulPool, options: [{ id: 0, materials: [] }, { id: 1, materials: [] }] } };
  const blankMarkup = renderToStaticMarkup(createElement(SoulPoolPage, { state: blank, action: () => {}, active: true }));
  assert.match(blankMarkup, /本级别暂无可用材料/, 'an empty plan names the real problem');
  assert.equal(blankMarkup.includes('材料或金币不足'), false, 'the generic hint does not cover an empty roll');
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
  assert.match(markup, /soul-requirement-source/, '每一格都写出材料来源插件');
  assert.match(markup, /Complete Alchemy &amp; Cooking Overhaul\.esp/, '来源写着具体插件名');
  assert.equal(markup.includes('缺 1'), false, 'the missing hint is gone');
});


test('upgrade preview uses the saved random gain for both plans', () => {
  for (const gain of [1, 10, 11, 20, 90, 91, 100]) {
    const state = { ...arrowDemo, soulPool: { ...arrowDemo.soulPool, capacity: 173, upgradeGain: gain } };
    const html = renderToStaticMarkup(createElement(SoulPoolPage, { state, action: () => {}, active: true }));
    assert.ok(html.includes(`<strong>+${gain}<small>点</small></strong>`));
    assert.ok(html.includes(`<b>${173 + gain}</b>`));
    assert.match(html, /本次容量增加/);
    assert.match(html, /扩容后上限/);
    assert.ok(html.indexOf('soul-upgrade-preview') < html.indexOf('soul-plans'));
    assert.match(html, /1～100/);
    assert.match(html, /读完存档不会改变/);
  }
});


test('ten material kinds per plan stay visible and the confirm action repeats the gain', () => {
  const pool = { ...arrowDemo.soulPool, upgradeGain: 100, options: [0, 1].map(id => ({ id,
    materials: Array.from({ length: 10 }, (_, n) => ({ id: id * 100 + n, name: `材料${n + 1}`, source: 'Skyrim.esm', count: n + 1, owned: 10 })) })) };
  const html = renderToStaticMarkup(createElement(SoulPoolPage, { state: { ...arrowDemo, soulPool: pool }, action: () => {}, active: true }));
  assert.equal((html.match(/10 种材料/g) ?? []).length, 2);
  assert.equal((html.match(/class="soul-requirement-label"/g) ?? []).length, 20);
  assert.match(html, /按方案甲扩容 · \+100 点/);
  assert.match(html, /按方案乙扩容 · \+100 点/);
});


test('panel soul segments retain exact fractions after expansion and handle empty capacity',()=>{
  const widths=(points,capacity)=>{
    const html=renderToStaticMarkup(createElement(SoulPoolPage,{state:{...arrowDemo,soulPool:{...arrowDemo.soulPool,points,capacity}},action:()=>{},active:true}));
    assert.match(html,/aria-label="灵魂池容量"/);
    return [...html.matchAll(/<span style="width:([^%]+)%"/g)].map(m=>Number(m[1]));
  };
  assert.deepEqual(widths(12,20),[...Array(12).fill(100),...Array(8).fill(0)]);
  assert.deepEqual(widths(125,200),[...Array(12).fill(100),50,...Array(7).fill(0)]);
  assert.deepEqual(widths(0,20),Array(20).fill(0));
  assert.deepEqual(widths(20,20),Array(20).fill(100));
  assert.deepEqual(widths(30,20),Array(20).fill(100));
  assert.deepEqual(widths(12,0),Array(20).fill(0));
});
