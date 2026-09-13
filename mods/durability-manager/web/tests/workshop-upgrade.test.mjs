import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';

const native = readFileSync(new URL('../../native/src/main.cpp', import.meta.url), 'utf8');
const begin = native.indexOf('void ApplyEnhancementCard(');
const apply = native.slice(begin, native.indexOf('void ', begin + 25));

test('equipped enhancement source contract: validate, unequip, re-resolve, then pay once', () => {
  // Engine integration guards, not a substitute for an in-game equip/unequip test.
  assert.doesNotMatch(native, /blockedReason = "请先卸下装备"|SendState\("请先卸下该装备再替换附魔/);
  assert.ok(apply.indexOf('player->GetItemCount(material)') < apply.indexOf('equipment.Prepare()'));
  assert.ok(apply.indexOf('equipment.Prepare()') < apply.indexOf('player->RemoveItem(material, count'));
  assert.equal((apply.match(/player->RemoveItem\(material, count/g) ?? []).length, 1);
  assert.match(apply, /instance = ResolveEquipmentInstance\(\*key\);/);
  assert.match(apply, /const auto restored = equipment.Restore\(\);/);
  assert.ok(apply.indexOf('equipment.LeaveUnequipped()') < apply.indexOf('DowngradeProtectedEquipment'));
  assert.ok(apply.indexOf('equipment.LeaveUnequipped()') < apply.indexOf('player->RemoveItem(instance->item'));
  assert.match(apply, /金币和材料已退还/);
});

test('restore source contract: exact instance, original hands, occupied-slot guard, no force', () => {
  const restore = native.slice(native.indexOf('class WorkshopEquipmentRestore'), begin);
  assert.match(restore, /ItemKey key_;/);
  assert.match(restore, /GetCount\(\) > 1/);
  assert.match(restore, /slotID_ = .*0x13F45.*left \? 0x13F43 : 0x13F42/);
  assert.match(restore, /player->GetEquippedObject\(false\)/);
  assert.match(restore, /player->GetEquippedObject\(true\)/);
  assert.match(restore, /otherArmor->GetSlotMask\(\)/);
  assert.match(restore, /UnequipObject\(.*false, false, false, true\)/);
  assert.match(restore, /EquipObject\(.*false, false, false, true\)/);
  assert.ok((restore.match(/ResolveEquipmentInstance\(key_\)/g) ?? []).length >= 4);
});

test('one gold fee feeds the same material ledger as recipe gold', () => {
  const costs = native.slice(native.indexOf('GetCardMaterials('), native.indexOf('EligibleCardTypes('));
  assert.equal((costs.match(/enhancement::GoldFee\(/g) ?? []).length, 1);
  assert.match(costs, /materials\[material\]/);
  assert.doesNotMatch(costs, /lateGold \* extra/);
});

test('workshop audio defaults to failure and plays success only at native outcomes', () => {
  assert.match(native, /if \(g_settings.enableWorkshopSounds\) RE::PlaySound/);
  assert.match(native, /resultSound = "UIMenuCancel"/);
  assert.match(apply, /feedback.resultSound = "UIEnchantingItemCreate"/);
  assert.match(apply, /feedback.resultSound = "UIEnchantingItemDestroy"/);
  assert.match(native, /"UISmithingImproveWeapon" : "UISmithingImproveArmor"/);
  assert.match(native, /key == "ENABLEWORKSHOPSOUNDS"/);
  const app = readFileSync(new URL('../src/App.tsx', import.meta.url), 'utf8');
  const settings = readFileSync(new URL('../src/EquipmentSettings.tsx', import.meta.url), 'utf8');
  assert.match(settings, /aria-label="工坊操作音效"/);
  assert.match(app, /enableWorkshopSounds: flag\(rawSettings.enableWorkshopSounds, true\)/);
});

test('all seven card types have distinct fills and tiers have increasing depth', () => {
  const css = readFileSync(new URL('../src/styles.css', import.meta.url), 'utf8');
  const colors = [];
  for (const type of ['performance', 'weight', 'speed', 'durability', 'wear', 'charge', 'enchantment']) {
    colors.push(css.match(new RegExp(`\\.enhancement-card\\.${type} \\{ --card-rgb: ([^;]+);`))?.[1]);
  }
  assert.ok(colors.every(Boolean));
  assert.equal(new Set(colors).size, 7);
  assert.match(css, /--card-depth: \.14/);
  assert.match(css, /--card-depth: \.44/);
});
