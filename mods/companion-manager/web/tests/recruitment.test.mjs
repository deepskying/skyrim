import { test } from "node:test";
import assert from "node:assert/strict";
import { fixture, simulate } from "./fixture.mjs";
import { recruitmentCandidates, recruitmentBlock } from "../src/recruitment.ts";

test("recruitment lists nearby people and unmanaged teammates, with search and rejection reasons", () => {
  const s = fixture();
  const teammate = { ...s.followers[0], id: "00000022", managed: false, canRecruit: true };
  s.followers.push(teammate);
  assert.deepEqual(new Set(recruitmentCandidates(s, "").map(a => a.id)),
    new Set(["00013486", "00013487", teammate.id]));
  assert.deepEqual(recruitmentCandidates(s, "莱迪亚"), [teammate]);
  assert.equal(recruitmentBlock(s, teammate, false), "");
  teammate.canRecruit = false;
  teammate.reason = "人物正在参与剧情场景";
  assert.equal(recruitmentBlock(s, teammate, false), teammate.reason);
  assert.match(recruitmentBlock(s, teammate, true), /正在处理/);
  assert.match(recruitmentBlock(null, teammate, false), /进入游戏/);
  s.managerAvailable = false;
  assert.match(recruitmentBlock(s, teammate, false), /CompanionManager.esp/);
});

test("two independent recruitments add both actors without removing the original teammate", () => {
  const s = fixture(), original = s.followers[0];
  const targets = recruitmentCandidates(s, "");
  for (const actor of targets) {
    assert.equal(recruitmentBlock(s, actor, false), "");
    const request = { session: s.session, command: "recruit", actorId: actor.id };
    assert.equal(simulate(s, request).ok, true);
    assert.equal(simulate(s, request).ok, false);
    assert.equal(actor.group, "party");
    assert.equal(actor.levelCap, 300);
  }
  assert.equal(original.managed, true);
  assert.equal(original.group, "party");
  assert.equal(s.followers.filter(a => a.group === "party").length, 3);
  assert.equal(recruitmentCandidates(s, "").length, 0);
});

test("dismissed records count toward capacity; rejected or stale recruitment leaves the roster unchanged", () => {
  const s = fixture(), target = s.followers[2];
  for (let i = 2; i < 64; i++) s.followers.push({ ...s.followers[1], id: (0x100000 + i).toString(16).padStart(8, "0") });
  assert.match(recruitmentBlock(s, target, false), /64 位名册已满/);
  const before = structuredClone(s);
  assert.equal(simulate(s, { session: s.session, command: "recruit", actorId: target.id }).ok, false);
  assert.deepEqual(s, before);
  assert.equal(simulate(s, { session: "old-save", command: "recruit", actorId: target.id }).ok, false);
  assert.deepEqual(s, before);
});
