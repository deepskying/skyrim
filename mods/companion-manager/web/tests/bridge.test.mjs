import { test } from "node:test";
import assert from "node:assert/strict";
import {
  parseSnapshot,
  readSnapshot,
  isGameLocation,
  percent,
  closeKey,
} from "../src/bridge.ts";
import { fixture } from "./fixture.mjs";
const snapshot = fixture;

test("accepts a native snapshot, including zero resources and cross-world unknown distance", () => {
  const s = snapshot();
  s.followers[0].magicka = [0, 0];
  s.followers[0].distance = null;
  assert.deepEqual(parseSnapshot(s), s);
  assert.equal(percent(12, 0), 0);
  assert.equal(percent(120, 100), 100);
  assert.equal(percent(NaN, 100), 0);
});
test("rejects incompatible data instead of substituting demo followers", () => {
  for (const mutate of [
    (s) => (s.version = 1),
    (s) => (s.followers[0].limited = true),
    (s) => s.followers.push(s.followers[0]),
    (s) => (s.followers[0].health = [NaN, 100]),
    (s) => (s.followers[0].gear[0].count = -1),
    (s) => s.followers[0].spells.push(s.followers[0].spells[0]),
    (s) => (s.followers[0].id = "lydia"),
    (s) => (s.followers[0].group = "unknown"),
  ]) {
    const s = snapshot();
    mutate(s);
    assert.equal(parseSnapshot(s), null);
  }
  assert.equal(parseSnapshot(null), null);
  assert.equal(parseSnapshot({}), null);
});
test("empty and unloaded saves are valid, old rows are not retained", () => {
  const s = snapshot();
  s.followers = [];
  s.ready = false;
  assert.equal(parseSnapshot(s).followers.length, 0);
});

test("a clean snapshot needs no repair and reports nothing", () => {
  const { snapshot: read, issues } = readSnapshot(snapshot());
  assert.ok(read);
  assert.deepEqual(issues, []);
});

// Regression: equipping an item makes the engine copy the pack stack's ExtraUniqueID onto the
// worn copy, so one key described two instances and the whole panel went blank. The repair
// layer keeps one row per key and the strict validator still rejects the raw payload.
test("duplicated instance keys are collapsed instead of blanking the panel", () => {
  const s = snapshot();
  const row = s.followers[0].wardrobe[0];
  s.followers[0].wardrobe.splice(1, 0, { ...row, count: 5, equipped: false });
  assert.equal(parseSnapshot(s), null);
  const { snapshot: read, issues } = readSnapshot(s);
  assert.ok(read);
  const keys = read.followers[0].wardrobe.map((i) => i.key);
  assert.equal(new Set(keys).size, keys.length);
  assert.equal(keys.filter((k) => k === row.key).length, 1);
  assert.match(issues.join(" "), /伙伴库存/);
});

test("one unusable follower row no longer hides the others", () => {
  const s = snapshot();
  s.followers[1].id = "lydia";
  const { snapshot: read, issues } = readSnapshot(s);
  assert.ok(read);
  assert.equal(read.followers.length, s.followers.length - 1);
  assert.match(issues.join(" "), /已跳过 1 名/);
});

test("inconsistent values are repaired, not rejected", () => {
  const s = snapshot();
  const skills = s.followers[0].skills.length;
  s.followers[0].health = [NaN, 100];
  s.followers[0].skills[0].value = NaN;
  s.followers[0].limited = true;
  s.followers[0].levelCap = null;
  s.settings.opacity = 100;
  const { snapshot: read, issues } = readSnapshot(s);
  assert.ok(read);
  assert.deepEqual(read.followers[0].health, [0, 100]);
  assert.equal(read.followers[0].skills.length, skills - 1);
  assert.equal(read.followers[0].limited, false);
  assert.equal(read.settings.opacity, 96);
  assert.ok(issues.length);
});

test("oversized lists are trimmed with a notice", () => {
  const s = snapshot();
  s.inventory = Array.from({ length: 513 }, (_, i) => ({
    ...s.inventory[0],
    id: i.toString(16).toUpperCase().padStart(8, "0"),
  }));
  const { snapshot: read, issues } = readSnapshot(s);
  assert.ok(read);
  assert.equal(read.inventory.length, 512);
  assert.ok(issues.length);
});

test("a payload that cannot be repaired is still reported with a reason", () => {
  const s = snapshot();
  s.version = 1;
  const { snapshot: read, issues } = readSnapshot(s);
  assert.equal(read, null);
  assert.match(issues[0], /无法解析/);
  assert.deepEqual(readSnapshot(undefined).issues, []);
});
test("game origin never defaults to the demo when the native bridge is late", () => {
  assert.equal(isGameLocation("mod:", ""), true);
  assert.equal(isGameLocation("http:", "?runtime=game"), true);
  assert.equal(isGameLocation("http:", ""), false);
});
test("close chord respects typing, modifiers, repeats and IME", () => {
  const e = {
    key: "F",
    code: "KeyF",
    shiftKey: true,
    ctrlKey: false,
    altKey: false,
    metaKey: false,
    repeat: false,
    isComposing: false,
  };
  assert.equal(closeKey(e, false), true);
  assert.equal(closeKey(e, true), false);
  for (const flag of ["ctrlKey", "altKey", "metaKey", "repeat", "isComposing"])
    assert.equal(closeKey({ ...e, [flag]: true }, false), false);
  assert.equal(closeKey({ ...e, shiftKey: false }, false), false);
  assert.equal(closeKey({ ...e, key: "Escape" }, true), true);
});

test("validates native command identifiers, settings, and player inventory", () => {
  for (const mutate of [
    (s) => (s.session = ""),
    (s) => (s.managerAvailable = 1),
    (s) => (s.settings.opacity = 101),
    (s) => (s.settings.distance = -1),
    (s) => (s.inventory[0].id = "book"),
    (s) => (s.inventory[0].count = 1.5),
    (s) => (s.followers[0].spells[0].id = "0"),
    (s) => (s.followers[0].resistances[0].value = Infinity),
  ]) {
    const s = snapshot();
    mutate(s);
    assert.equal(parseSnapshot(s), null);
  }
});
test("allows managed registry, disabled spells, and negative resistance", () => {
  const s = snapshot();
  s.followers[1].spells[0].enabled = false;
  assert.ok(parseSnapshot(s));
});

test("accepts 64 managed companions plus external candidates, capped at 128 rows", () => {
  const s = snapshot(), base = s.followers[0];
  s.followers = Array.from({ length: 128 }, (_, i) => ({
    ...structuredClone(base), id: (0x10000 + i).toString(16).padStart(8, "0").toUpperCase(),
    managed: i < 64, limited: i >= 64, canRecruit: i >= 64,
  }));
  assert.equal(parseSnapshot(s)?.followers.filter(f => f.managed).length, 64);
  s.followers.push({ ...structuredClone(base), id: "00020000" });
  assert.equal(parseSnapshot(s), null);
});
