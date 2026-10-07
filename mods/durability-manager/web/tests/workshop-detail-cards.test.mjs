import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';

const app = readFileSync(new URL('../src/App.tsx', import.meta.url), 'utf8');
const nav = readFileSync(new URL('../src/WorkshopNavigation.tsx', import.meta.url), 'utf8');
const css = readFileSync(new URL('../src/workshop.css', import.meta.url), 'utf8');

test('the enhancement rail entry is gone', () => {
  assert.match(nav, /export type Tab = 'workshop' \| 'arrows' \| 'soul' \| 'divine' \| 'settings'/);
  // No rail entry declares it any more - the comment above the type still explains why.
  assert.doesNotMatch(nav, /name: '装备强化'/);
  assert.doesNotMatch(nav, /id: 'enhancement'/);
  assert.doesNotMatch(app, /tab === 'enhancement'/);
  assert.doesNotMatch(app, /EquipmentEnhancementGrid/);
});

test('the detail panel offers repair and enhancement as two cards', () => {
  assert.match(app, /className="action-cards"/);
  assert.match(app, /"action-card repair"/);
  assert.match(app, /"action-card enhance"/);
  assert.match(app, /action-card-icon">⚒/);
  assert.match(app, /action-card-icon">✦/);
  // The card keeps the wording the forge-access contract test greps for, and the repair button
  // still reports why it is unavailable.
  assert.match(app, /强化和刷新需要靠近附魔台或锻造设备/);
  assert.match(app, /!state\.forge\.active \? '需锻造设施'/);
  // The old strips are gone, and the enhancement page itself is still reached from the card.
  assert.doesNotMatch(app, /action-strip/);
  assert.match(app, /setEnhancingId\(selected\.id\)/);
  assert.match(app, /enhancing \? <EnhancementPage/);
});

test('the two cards are styled as a responsive pair', () => {
  assert.match(css, /\.action-cards\{display:grid;grid-template-columns:repeat\(2,minmax\(0,1fr\)\)/);
  assert.match(css, /\.action-card\.enhance\{/);
  assert.match(css, /@media\(max-width:1100px\)\{\.action-cards\{grid-template-columns:1fr\}\}/);
});
