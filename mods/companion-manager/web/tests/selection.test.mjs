import {test} from 'node:test';
import assert from 'node:assert/strict';
import {pinnedCompanionId} from '../src/companion-selection.ts';
const roster=(...ids)=>ids.map(id=>({id}));
test('the pinned companion survives a distance-ordered roster reshuffle',()=>{
  const first=roster('AAA','BBB','CCC');
  assert.equal(pinnedCompanionId('',first),'AAA');          // first entry only used to seed
  const chosen=pinnedCompanionId('CCC',first);
  assert.equal(chosen,'CCC');
  assert.equal(pinnedCompanionId(chosen,roster('BBB','AAA','CCC')),'CCC'); // walk order changed
  assert.equal(pinnedCompanionId(chosen,roster('CCC','AAA','BBB')),'CCC');
});
test('only a player or dialogue choice moves the panel',()=>{
  assert.equal(pinnedCompanionId('CCC',[]),'CCC');                  // data not delivered yet
  assert.equal(pinnedCompanionId('CCC',roster('AAA','BBB')),'CCC'); // left the roster: keep waiting
  assert.equal(pinnedCompanionId('',[]),'');
  assert.equal(pinnedCompanionId('DDD',roster('AAA')),'DDD');       // a dialogue request is respected
});
