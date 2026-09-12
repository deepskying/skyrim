const {test} = require('node:test');
const assert = require('node:assert/strict');
const Volume = require('./volume-control.js');
function fixture() {
  const commands = []; let clock = 0;
  const volume = new Volume(command => commands.push(command), 'test-session', () => clock);
  return {volume, commands, advance: ms => { clock += ms; }};
}
test('polling cannot reset a mouse draft before change, even without element focus', () => {
  const {volume, commands} = fixture();
  volume.receive(.5); volume.begin(); volume.input(17);
  volume.receive(.5);
  assert.equal(volume.percent, 17);
  volume.finish();
  assert.equal(commands[0].value, .17);
  volume.receive(.5);
  assert.equal(volume.percent, 17);
  volume.receive(.17, commands[0].requestId);
  assert.equal(volume.pending, false);
});
test('earlier replies cannot overwrite the final value, including after confirmation', () => {
  const {volume, commands} = fixture();
  for (const value of [20, 50, 20]) { volume.input(value); volume.flush(); }
  volume.finish();
  volume.receive(.2, commands[0].requestId);
  assert.equal(volume.pending, true);
  volume.receive(.5, commands[1].requestId);
  assert.equal(volume.percent, 20);
  volume.receive(.2, commands[2].requestId);
  assert.equal(volume.pending, false);
  volume.receive(.5, commands[1].requestId);
  assert.equal(volume.percent, 20);
});
test('live adjustment acknowledgement does not overwrite a newer unsent draft', () => {
  const {volume, commands} = fixture();
  volume.input(70); volume.flush(); volume.input(30);
  volume.receive(.7, commands[0].requestId);
  assert.equal(volume.percent, 30);
  volume.finish();
  assert.equal(commands.at(-1).value, .3);
});
test('keyboard/blur commits, endpoints, duplicate pointerup and synchronous preview replies', () => {
  let volume;
  volume = new Volume(command => volume.receive(command.value, command.requestId), 'preview');
  volume.input(0); volume.finish();
  assert.equal(volume.percent, 0); assert.equal(volume.pending, false);
  const sequence = volume.sequence;
  volume.finish(); assert.equal(volume.sequence, sequence);
  volume.input(100); volume.finish(); assert.equal(volume.percent, 100);
});
test('request identifiers differ when a panel is reloaded', () => {
  const one = new Volume(() => {}, 'session-a'), two = new Volume(() => {}, 'session-b');
  one.input(30); one.finish(); two.input(30); two.finish();
  assert.notEqual(one.requestId, two.requestId);
});
test('missing confirmation and save failure are visible instead of pretending persistence', () => {
  const {volume, commands, advance} = fixture();
  volume.input(23); volume.finish(); advance(6000);
  assert.match(volume.message, /尚未确认/);
  volume.receive(.23, commands[0].requestId, '保存失败');
  assert.equal(volume.message, '保存失败');
  volume.input(24); volume.finish();
  volume.receive(.24, commands[1].requestId);
  assert.equal(volume.message, '');
});
