import { test } from "node:test";
import assert from "node:assert/strict";
import { fixture, simulate } from "./fixture.mjs";
import { plainDescription, teachingBlock } from "../src/magic.ts";
test("teaching is available for a managed actor with an unused spellbook", () => {
  const s = fixture();
  assert.equal(teachingBlock(s, s.followers[0], s.inventory[0], false), "");
});
test("missing ESP, foreign follower and quest book have actionable reasons", () => {
  const s = fixture(),
    f = s.followers[0],
    b = s.inventory[0];
  s.managerAvailable = false;
  assert.match(teachingBlock(s, f, b, false), /CompanionManager.esp/);
  s.managerAvailable = true;
  f.managed = false;
  f.canRecruit = true;
  assert.match(teachingBlock(s, f, b, false), /点击上方「纳入同行管理」/);
  f.managed = true;
  b.quest = true;
  assert.match(teachingBlock(s, f, b, false), /任务/);
  b.quest = false;
  b.count = 0;
  assert.match(teachingBlock(s, f, b, false), /没有/);
});
test("already-known disabled spells and pending commands cannot consume a book twice", () => {
  const s = fixture(),
    f = s.followers[0],
    b = s.inventory[0];
  assert.match(teachingBlock(s, f, b, true), /正在处理/);
  f.spells.push({
    id: b.spellId,
    name: b.spellName,
    school: "恢复系",
    cost: 73,
    enabled: false,
  });
  assert.match(teachingBlock(s, f, b, false), /已掌握/);
});
test("book formatting is displayed as text, retaining line breaks", () => {
  assert.equal(
    plainDescription('<font face="test">恢复 50 点<br/>生命 &amp; 法力</font>'),
    "恢复 50 点\n生命 & 法力",
  );
  assert.equal(plainDescription('<img src="evil"/>'), "");
});
test("an existing teammate can enroll before teaching, with one book consumed and repeat blocked", () => {
  const s = fixture(), f = s.followers[0], b = s.inventory[0];
  f.managed = false;
  f.limited = true;
  f.canRecruit = true;
  const request = (command, data = {}) => simulate(s, {
    session: s.session, actorId: f.id, command, ...data,
  });
  assert.match(teachingBlock(s, f, b, false), /纳入同行管理/);
  assert.equal(request("teach", { entityId: b.id }).ok, false);
  assert.equal(b.count, 2);
  assert.equal(request("adopt").ok, true);
  assert.equal(f.group, "party");
  assert.equal(request("adopt").ok, false);
  assert.equal(teachingBlock(s, f, b, false), "");
  assert.equal(request("wait", { value: true }).ok, true);
  assert.equal(f.waiting, true);
  assert.equal(request("teach", { entityId: b.id }).ok, true);
  assert.equal(b.count, 1);
  assert.match(teachingBlock(s, f, b, false), /已掌握/);
  assert.equal(request("teach", { entityId: b.id }).ok, false);
  assert.equal(b.count, 1);
});
