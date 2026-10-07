# Skyrim PrismaUI Mods

This repository keeps the Skyrim SE SKSE + PrismaUI mods together while preserving each mod as an independent build and install unit.

## Modules

- `mods/wilderness-encounters` — 野外随机群落袭击、中文案例事件和双方火拼；每场 3–20 名参与者，可选接入扩展怪物。测试版本 0.2.1，默认频繁，包含 119 组可选扩展群落，目标 Skyrim SE **1.5.97**。
- `mods/arcane-arsenal` — weapon, staff and greatsword assets with their art and material build pipeline (`art/` holds the sources, `build/` the per-version working copies its scripts read as baselines).
- `mods/buy-displayed-items` — purchase merchant-owned displayed items in shops and inns with the normal interaction key; sneak to steal. Independent SKSE plugin for **1.5.97**; first test build, no PrismaUI required.
- `mods/companion-manager` — follower dashboard running on the Meridian UI platform. Default panel hotkey: **Shift+F**.
- `mods/magic-arrows` — arrow crafting, charging rules and the crafting queue; the unified workshop consumes its ESP.
- `mods/divine-blood` — 神之血 1.0.0：保留旧插件身份，16 种独立模型及 SPID 分发；装备工坊 2.4.0 在炼金台附近使用共享灵魂池与临时炼金池炼制。
- `mods/meridian-ui` — the UI platform itself: Meridian UI 1.5.0 sources plus the local NIF preview patch. See `mods/meridian-ui/FORK-NOTES.md` before changing it.
- `mods/main-menu-manager` — random main-menu themes, a separate loading-screen library, desktop preview/removal with synchronized LSCR records, resource recovery, and an offline helper for custom images. Targets Skyrim SE **1.5.97**; no PrismaUI required.
- `mods/music-manager` — environment-aware MP3 background music, DCS library migration, and Prisma UI controls. Default panel hotkey: **Shift+M**. Targets Skyrim SE **1.5.97**.
- `mods/peak-effect-loop-guard` — stops magic effects that would otherwise loop forever.
- `mods/condition-actor-guard` — stops the 1.5.97 actor-only condition functions from dereferencing a null actor when a spell, perk or package condition is evaluated against a non-actor target. Targets Skyrim SE **1.5.97**; no PrismaUI required.
- `mods/inventory-manager` — lightweight inventory and magic list with configurable shortcuts. Default panel hotkey: **Shift+D**.
- `mods/durability-manager` — PrismaUI foundation for weapon and armour durability. Default panel hotkey: **Shift+F**.
- `mods/workshop` — the unified equipment workshop (durability, arrow crafting queue, divine blood, status HUD). It uses sources from `durability-manager`, `magic-arrows` and `divine-blood`; the workshop package includes all three modules while retaining their ESP identities. Hotkey: **Shift+A**.

Both mods can be installed together: they use separate DLLs, views, and INI files. Shared Iconfont source is under `shared/iconfont`; the external build dependencies stay in `reference/`.

## Tools

- `tools/weapon-balancer` — local web GUI that reads the active MO2 load order and normalises mod-added weapon damage and attack speed per animation type. It lists every weapon record with the effective (post-override) values, takes per-category caps and per-weapon overrides, previews the change list, exports it as CSV, and generates the ESL patch plugin `武器平衡-WeaponRebalance` that applies the changes without touching any original mod file. See `tools/weapon-balancer/README.md`.

## Follower Spellbook Manager

> Removed from this repository on 2026-09-25; the sections below are kept as history.

An SKSE + Prisma UI mod for Skyrim Special Edition 1.5.97. It lets the player inspect loaded followers' spells and teach them spell tomes from the player's inventory.

## Current behavior

- Press **Shift+S** to open or close the panel. The hotkey is configurable through `SKSE/Plugins/FollowerSpellbookManager.ini`.
- Click the close button or press **Esc** to close the panel from any page.
- Open to a grid of loaded player teammates. Each card shows the follower's class, level, and live health, magicka, and stamina bars before opening the detail page.
- Player-scaled followers show their current level cap on the roster card. Their detail page can raise that cap to the configured target and later restore the original value; fixed-level followers are left unchanged.
- The responsive panel uses 90% of the available viewport and a translucent blue-green theme.
- View that follower's castable spells in an independently scrolling grid, with each card showing the calculated cost and its share of the follower's maximum magicka.
- Enable or disable individual follower spells from each spell card. Disabled spells remain visible for restoration, and their state is stored in the SKSE co-save.
- Filter the list by magic school.
- Browse spell tomes in an independently scrolling grid. Each card shows its stack count, gold value, school, and calculated magicka cost.
- Hover or focus a tome to preview the game's localized spell description in the details area below; click it to select it for teaching.
- Teach the selected spell tome to the current follower.
- The tome is removed only after `Actor::AddSpell` succeeds.
- Each successful teaching is also stored in the SKSE co-save. On a later load, the plugin resolves the saved FormIDs and reapplies any tracked spell that a current player teammate is missing.

## Runtime requirements

- Skyrim SE 1.5.97 and the matching SKSE64 build
- Address Library for SKSE Plugins
- Media Keys Fix SKSE
- Prisma UI

The current MO2 profile already contains these requirements. The mod is deliberately not copied into MO2 until its native DLL has compiled and been tested.

## Hotkey configuration

After installing the mod, edit `SKSE/Plugins/FollowerSpellbookManager.ini` in its MO2 mod folder, then restart the game. The default is Shift+S:

```ini
[Hotkey]
Key=S
Shift=true
Ctrl=false
Alt=false

[LevelScaling]
MaxLevel=300
```

`Key` accepts A–Z, 0–9, F1–F12, Esc, Tab, Enter, Space, or a DirectInput scan code such as `0x1F`. Set a modifier to `true` when it must be held. For example, Ctrl+Alt+M is `Key=M`, `Ctrl=true`, `Alt=true`, `Shift=false`. `LevelScaling.MaxLevel` accepts 1–1000 and defaults to 300.

## Build

1. Ensure the repository-level `reference/` directory contains the Prisma UI example repositories and their submodules.
2. In `mods/follower-spellbook-manager/web/`, run `npm install` followed by `npm run build`.
3. In `mods/follower-spellbook-manager/native/`, run `xmake build -y`.

The web build produces the Prisma view. The native build produces the SKSE plugin DLL. A later packaging step combines them under the MO2 mod directory structure. See `mods/inventory-manager/README.md` for the inventory mod's own controls and packaging steps.
