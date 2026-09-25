import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import { test } from 'node:test';
import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import ts from 'typescript';

const source = readFileSync(new URL('../src/EquippedHud.tsx', import.meta.url), 'utf8');
const compiled = ts.transpileModule(source, { compilerOptions: { jsx: ts.JsxEmit.ReactJSX, module: ts.ModuleKind.CommonJS } }).outputText;
const exports = {};
const require = createRequire(import.meta.url);
new Function('require', 'exports', compiled)((name) => name === './format' ? { formatDurability: value => value.toFixed(1) } : require(name), exports);

test('large equipped snapshot stays bounded and reports hidden count', () => {
  const previousWindow = globalThis.window;
  globalThis.window = { innerHeight: 720 };
  try {
    const items = Array.from({ length: 30 }, (_, index) => ({ id: `${index}`, kind: 'weapon', title: `剑${index}`, detail: '右手', current: 50, maximum: 100 }));
    const normal = renderToStaticMarkup(createElement(exports.EquippedHud, { items }));
    const notified = renderToStaticMarkup(createElement(exports.EquippedHud, { items, hasNotification: true }));
    const normalCount = (normal.match(/class="durability-hud equipped-hud-item/g) ?? []).length;
    const notifiedCount = (notified.match(/class="durability-hud equipped-hud-item/g) ?? []).length;
    assert.ok(normalCount > 0 && normalCount < 30);
    assert.ok(notifiedCount < normalCount);
    assert.match(normal, new RegExp(`另有 ${30 - normalCount} 件装备`));
    assert.match(notified, new RegExp(`另有 ${30 - notifiedCount} 件装备`));
  } finally {
    globalThis.window = previousWindow;
  }
});
