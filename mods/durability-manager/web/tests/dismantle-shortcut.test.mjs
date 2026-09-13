import assert from 'node:assert/strict';
import test from 'node:test';
import { readFileSync } from 'node:fs';
import ts from 'typescript';
const source = readFileSync(new URL('../src/dismantle-shortcut.ts', import.meta.url), 'utf8');
const js = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.ESNext } }).outputText;
const { defaultDismantleHotkey: binding, shortcutAllowed, matchesShortcut, shortcutLabel } = await import(`data:text/javascript;base64,${Buffer.from(js).toString('base64')}`);
const context = { visible: true, page: 'dismantle', forge: true, editing: false, busy: false, protectedItem: false, selectedId: '42:7', eventId: '42:7' };
const event = { key: 'D', shiftKey: true, ctrlKey: false, altKey: false, repeat: false };
test('direct dismantling requires focused recycling context and the same selected instance', () => {
  assert.equal(shortcutAllowed(context), true);
  for (const change of [{ visible: false }, { page: 'workshop' }, { page: 'settings' }, { forge: false }, { editing: true }, { busy: true }, { protectedItem: true }, { selectedId: undefined }, { eventId: '42:8' }]) assert.equal(shortcutAllowed({ ...context, ...change }), false);
});
test('shortcut is exact, ignores repeat/composition and can be disabled', () => {
  assert.equal(matchesShortcut(event, binding), true);
  assert.equal(matchesShortcut({ ...event, key: 'd' }, binding), true);
  for (const change of [{ repeat: true }, { isComposing: true }, { ctrlKey: true }, { altKey: true }, { shiftKey: false }, { key: 'F' }]) assert.equal(matchesShortcut({ ...event, ...change }, binding), false);
  assert.equal(matchesShortcut(event, { ...binding, enabled: false }), false);
});
test('custom Delete with modifiers matches and displays correctly', () => {
  const custom = { key: 'Delete', shift: false, ctrl: true, alt: true, enabled: true };
  assert.equal(shortcutLabel(custom), 'Ctrl + Alt + Delete');
  assert.equal(matchesShortcut({ ...event, key: 'Delete', shiftKey: false, ctrlKey: true, altKey: true }, custom), true);
  assert.equal(matchesShortcut(event, custom), false);
});
