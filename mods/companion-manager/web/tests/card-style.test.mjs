import {test} from 'node:test';
import assert from 'node:assert/strict';
import {cardAlpha,cardStrongAlpha,followerState} from '../src/card-style.ts';
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

test('the follower grid reads its tone, badge and footer from the party state',()=>{
  // Tone names are shared with the wardrobe grid's palette: party / waiting / registry / nearby.
  assert.deepEqual(followerState({managed:true,group:'party',waiting:false}),
    {tone:'party',badge:'同行中',status:'正在同行'});
  assert.deepEqual(followerState({managed:true,group:'party',waiting:true}),
    {tone:'waiting',badge:'等待中',status:'原地等待'});
  assert.deepEqual(followerState({managed:true,group:'registry'}),
    {tone:'registry',badge:'已离队',status:'已离队'});
  assert.deepEqual(followerState({managed:false,group:'nearby',canRecruit:true}),
    {tone:'nearby',badge:'待纳入',status:'待纳入管理'});
  assert.deepEqual(followerState({managed:false,group:'nearby',canRecruit:false}),
    {tone:'nearby',badge:'外部',status:'外部随从'});
  // A corpse keeps its roster record but must never look like an active companion.
  assert.deepEqual(followerState({dead:true,managed:true,group:'party',waiting:true}),
    {tone:'dead',badge:'已死亡',status:'已死亡'});
  // Only the party tone means "following": waiting is a party member parked in place.
  const tones=[{managed:true,group:'party'},{managed:true,group:'party',waiting:true},
    {managed:true,group:'registry'},{managed:false,group:'nearby',canRecruit:true}].map(f=>followerState(f).tone);
  assert.deepEqual(tones,['party','waiting','registry','nearby']);
});
