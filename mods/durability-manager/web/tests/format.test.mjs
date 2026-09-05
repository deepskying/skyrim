import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';
import ts from 'typescript';

const source = readFileSync(new URL('../src/format.ts', import.meta.url), 'utf8');
const compiled = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.ESNext } }).outputText;
const { formatDurability } = await import(`data:text/javascript;base64,${Buffer.from(compiled).toString('base64')}`);

test('durability display keeps one decimal including whole numbers and zero', () => {
  for (const [input, expected] of [[100, '100.0'], [0, '0.0'], [98.64, '98.6'], [98.66, '98.7'], [0.04, '0.0'], [0.06, '0.1']]) {
    assert.equal(formatDurability(input), expected);
  }
  for (const input of [undefined, NaN, Infinity]) assert.equal(formatDurability(input), '—');
});

test('list, details and HUD format both values without rounding the stored state', () => {
  const app = readFileSync(new URL('../src/App.tsx', import.meta.url), 'utf8');
  for (const context of ['item', 'selected', 'hud']) {
    for (const field of ['current', 'maximum']) assert.ok(app.includes(`formatDurability(${context}.${field})`));
  }
  // Source-level guard against truncation before the HUD reaches the formatter.
  const native = readFileSync(new URL('../../native/src/main.cpp', import.meta.url), 'utf8');
  assert.match(native, /optional<float> a_current/);
  assert.match(native, /optional<float> a_maximum/);
  assert.match(native, /const auto current = durability.current;/);
  assert.match(native, /const auto maximum = durability.maximum;/);
});
