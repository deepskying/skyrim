import { test } from "node:test";
import assert from "node:assert/strict";
import {
  parseSnapshot,
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
