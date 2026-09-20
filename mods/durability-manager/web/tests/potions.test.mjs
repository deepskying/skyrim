import assert from 'node:assert/strict';
import test from 'node:test';
import { readFileSync } from 'node:fs';
import ts from 'typescript';
async function load(name) {
  const text = readFileSync(new URL(`../src/potions/${name}.ts`, import.meta.url), 'utf8');
  const js = ts.transpileModule(text, { compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 } }).outputText;
  return import(`data:text/javascript;base64,${Buffer.from(js).toString('base64')}`);
}
const { effectTraits, effectDescription, nextPotionIndex, normalizePotions } = await load('rules');
const { potionDemo } = await load('demo');
test('multi-effect potion retains distinct recovery, fortify, regeneration and resistance traits', () => {
  const p = potionDemo.items[6];
  assert.deepEqual(effectTraits(p).map(t => t.id), ['skill-0','fortify-health','regen-health','resist-magic','armor']);
  assert.equal(effectTraits({ ...p, effects: [...p.effects, p.effects[0]] }).length, 5);
  const mixed = effectTraits(potionDemo.items[7]);
  assert.deepEqual(mixed.map(t => t.tone), ['health','harmful']);
});
test('unmapped mod effects preserve each name and never masquerade as health restoration', () => {
  const p = potionDemo.items[0];
  const tags = effectTraits({ ...p, effects: [301,302].map(id => ({ ...p.effects[0], id, name: `Custom ${id}`, traits: ['other'] })) });
  assert.deepEqual(tags.map(t => t.name), ['Custom 301','Custom 302']);
  assert.equal(tags.some(t => t.id === 'restore-health'), false);
});
test('grid navigation respects row edges and incomplete final rows', () => {
  assert.equal(nextPotionIndex(2,8,3,'ArrowRight'),2);
  assert.equal(nextPotionIndex(3,8,3,'ArrowLeft'),3);
  assert.equal(nextPotionIndex(4,8,3,'ArrowUp'),1);
  assert.equal(nextPotionIndex(5,8,3,'ArrowDown'),7);
  assert.equal(nextPotionIndex(7,8,3,'ArrowRight'),7);
  assert.equal(nextPotionIndex(0,0,3,'ArrowDown'),-1);
});
test('invalid snapshots and empty inventory cannot produce a drinkable placeholder', () => {
  assert.equal(normalizePotions(null), undefined);
  assert.equal(normalizePotions({ items: [], token: 0 }), undefined);
  const p = potionDemo.items[0];
  const result = normalizePotions({ token: 5, items: [p,p,{ ...p,id:2,count:0 },{ ...p,id:3,usable:undefined }], message: '' });
  assert.equal(result.items.length,2); assert.equal(result.items[1].usable,false);
  assert.deepEqual(normalizePotions({ items: [],token:6 }).items, []);
});
test('effect description substitutes game placeholders without interpreting HTML', () => {
  assert.equal(effectDescription({ ...potionDemo.items[0].effects[0], description: '恢复 <mag> 点，持续 <dur> 秒。<b>说明</b>', duration: 10 }), '恢复 150 点，持续 10 秒。说明');
});

test('poisons remain visible but cannot be made drinkable by a snapshot', () => {
  const poison = potionDemo.items.find(p => p.poison);
  assert.ok(poison);
  const result = normalizePotions({ token: 1, items: [{ ...poison, usable: true }, potionDemo.items[7]] });
  assert.equal(result.items[0].poison, true);
  assert.equal(result.items[0].usable, false);
  assert.equal(result.items[1].poison, false);
  assert.equal(result.items[1].usable, true);
});
