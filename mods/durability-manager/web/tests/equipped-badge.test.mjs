import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import { test } from 'node:test';
import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import ts from 'typescript';

const source = readFileSync(new URL('../src/EquippedBadge.tsx', import.meta.url), 'utf8');
const compiled = ts.transpileModule(source, { compilerOptions: { jsx: ts.JsxEmit.ReactJSX, module: ts.ModuleKind.CommonJS } }).outputText;
const exports = {};
new Function('require', 'exports', compiled)(createRequire(import.meta.url), exports);
const render = (equipped) => renderToStaticMarkup(createElement(exports.EquippedBadge, { equipped }));

test('equipped badge renders explicit text and checkmark only for worn items', () => {
  assert.match(render(true), /class="equipped-badge"/);
  assert.match(render(true), /✓/);
  assert.match(render(true), /已装备/);
  assert.equal(render(false), '');
  assert.equal(render(undefined), '');
});

test('list and details use instance equipped state independently of selection or damage', () => {
  // Source-level wiring guard; the badge's actual markup is rendered above.
  const app = readFileSync(new URL('../src/App.tsx', import.meta.url), 'utf8');
  assert.match(app, /<EquippedBadge equipped=\{item\.equipped\} \/>/);
  assert.match(app, /<EquippedBadge equipped=\{selected\.equipped\} \/>/);
  const native = readFileSync(new URL('../../native/src/main.cpp', import.meta.url), 'utf8');
  assert.match(native, /\{ "equipped", a_extraList && a_extraList->GetWorn\(\) \}/);
});
