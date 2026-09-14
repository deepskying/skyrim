import assert from 'node:assert/strict';
import test from 'node:test';
import { readFileSync } from 'node:fs';
import ts from 'typescript';
const source = readFileSync(new URL('../src/shortcut.ts', import.meta.url), 'utf8');
const js = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.ESNext } }).outputText;
const { matchesShortcut } = await import(`data:text/javascript;base64,${Buffer.from(js).toString('base64')}`);
const binding = { key: 'D', shift: true, ctrl: false, alt: false, enabled: true };
const event = { key: 'D', shiftKey: true, ctrlKey: false, altKey: false, repeat: false };
test('shortcut is exact, ignores repeat/composition and can be disabled', () => {
  assert.equal(matchesShortcut(event, binding), true);
  assert.equal(matchesShortcut({ ...event, key: 'd' }, binding), true);
  for (const change of [{ repeat: true }, { isComposing: true }, { ctrlKey: true }, { altKey: true }, { shiftKey: false }, { key: 'F' }]) assert.equal(matchesShortcut({ ...event, ...change }, binding), false);
  assert.equal(matchesShortcut(event, { ...binding, enabled: false }), false);
});
test('custom Delete with modifiers matches correctly', () => {
  const custom = { key: 'Delete', shift: false, ctrl: true, alt: true, enabled: true };
  assert.equal(matchesShortcut({ ...event, key: 'Delete', shiftKey: false, ctrlKey: true, altKey: true }, custom), true);
  assert.equal(matchesShortcut(event, custom), false);
});
