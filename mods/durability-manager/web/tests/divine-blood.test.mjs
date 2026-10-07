import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import { test } from 'node:test';
import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import ts from 'typescript';
function load(name) {
  const source=readFileSync(new URL(`../src/${name}`,import.meta.url),'utf8');
  const compiled=ts.transpileModule(source,{compilerOptions:{target:ts.ScriptTarget.ES2022,jsx:ts.JsxEmit.ReactJSX,module:ts.ModuleKind.CommonJS}}).outputText;
  const exports={},require=createRequire(import.meta.url);
  new Function('require','exports',compiled)(id=>id==='./useArrowBridge'?{nextArrowRequest:()=>1}:id==='./divine-demo'?load('arrows/divine-demo.ts'):require(id),exports);
  return exports;
}
const {DivineBloodPage,DivinePoolStar}=load('arrows/DivineBlood.tsx');
const {arrowDemo}=load('arrows/demo.ts');
const render=state=>renderToStaticMarkup(createElement(DivineBloodPage,{state,active:true,action:()=>{}}));
test('sixteen divine cards and both pools use the shared capacity',()=>{
  const html=render(arrowDemo);
  assert.equal((html.match(/aria-pressed=/g)??[]).length,16);
  assert.match(html,/生命上限 \+5/);assert.match(html,/负重上限 \+5/);
  assert.match(html,/阿卡托什之血/);assert.match(html,/灵魂池/);assert.match(html,/炼金池/);
  assert.equal((html.match(/aria-valuemax="20"/g)??[]).length,2);
  assert.match(html,/仅选择材料/);assert.match(html,/成功后炼金池清空/);
  assert.match(html,/蓝山花数量/);assert.doesNotMatch(html,/红山花数量/);
  assert.doesNotMatch(html,/炼制数量/);assert.match(html,/class="divine-craft-button" disabled=""/);
  assert.match(html,/灵魂石/);assert.match(html,/炼金材料/);assert.match(html,/灵魂与炼金六芒星/);
  assert.match(html,/普通灵魂石（充满）数量/);
});
test('missing plugin and out-of-range stations explain why crafting is unavailable',()=>{
  const html=render({...arrowDemo,divineBlood:{...arrowDemo.divineBlood,available:false},craftingAccess:{magic:false,normal:false,alchemy:false}});
  assert.match(html,/神血插件或灵魂池尚未就绪/);assert.match(html,/请靠近炼金台/);
  assert.match(html,/class="divine-craft-button" disabled=""/);
});
test('triangle outlines independently advance along their perimeter',()=>{
  const renderStar=(souls,alchemy,capacity=20)=>renderToStaticMarkup(createElement(DivinePoolStar,{souls,alchemy,capacity}));
  const offsets=html=>[...html.matchAll(/stroke-dashoffset="([^"]+)"/g)].map(m=>Number(m[1]));
  assert.deepEqual(offsets(renderStar(0,0)),[100,100,100,100]);
  assert.deepEqual(offsets(renderStar(20,20)),[0,0,0,0]);
  const partial=renderStar(15,5);
  assert.deepEqual(offsets(partial),[25,25,75,75]);
  assert.match(partial,/aria-label="灵魂池"[^>]*aria-valuenow="15"/);
  assert.match(partial,/aria-label="炼金池"[^>]*aria-valuenow="5"/);
  assert.doesNotMatch(partial,/<rect|clipPath|divine-triangle-fill/);
  assert.deepEqual(offsets(renderStar(-5,30)),[100,100,0,0]);
  const unavailable=renderStar(12,8,0);
  assert.deepEqual(offsets(unavailable),[100,100,100,100]);
  assert.doesNotMatch(unavailable,/NaN|Infinity/);
});
