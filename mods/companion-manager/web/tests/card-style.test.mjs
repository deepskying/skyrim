import {test} from 'node:test';
import assert from 'node:assert/strict';
import {cardAlpha,cardStrongAlpha} from '../src/card-style.ts';
test('card surfaces stay translucent across the opacity range',()=>{
  for(const opacity of [55,70,82,96]){
    const alpha=cardAlpha(opacity);
    assert.ok(alpha>=0.34&&alpha<=0.72,`${opacity} -> ${alpha}`);
    assert.ok(alpha<0.9,'a card must never be opaque');
    assert.ok(cardStrongAlpha(alpha)<=0.9);
    assert.ok(cardStrongAlpha(alpha)>alpha,'the active card reads stronger than the resting one');
  }
  assert.equal(cardAlpha(82),0.56);           // default preference
  assert.equal(cardAlpha(Number.NaN),cardAlpha(82)); // malformed preference falls back
  assert.equal(cardAlpha(0),0.34);            // clamped low
  assert.equal(cardAlpha(100),0.72);          // clamped high
});
