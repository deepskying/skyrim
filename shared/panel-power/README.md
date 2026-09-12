# Panel powers

Each manager ships its own ESL-flagged ESP (Skyrim.esm is the only master), with
permanent local IDs `800` (SPEL) and `801` (MGEF). The native listener resolves the
spell through the plugin name, so it does not depend on load order. Rebuild with
`python shared/panel-power/build_plugins.py`; validate with
`python shared/panel-power/test_plugins.py` from the repository root.

The effect is an inert, silent Script archetype without Papyrus attachments.
Only player casts of that module's spell enqueue its panel callback. Queued work
is invalidated on save changes; failed loads do not grant powers. The callback
uses the existing panel path and refuses to take focus from another Prisma view.
No change is made to workstation eligibility, music pause behavior, or hotkeys.

The INI `[PanelPower] Enabled` setting is read on new game/successful load. `1`
adds the power only if missing, preserving existing favorites; `0` removes it.
Removing and re-adding a power may require favoriting it again.

## In-game acceptance checks (require Skyrim)

- Enable each ESP alongside its updated DLL; load an existing save and verify
  all installed modules' powers appear with their Chinese names, once each.
- Favorite, equip and cast each power using keyboard and controller. Verify
  only the corresponding panel opens and can close with Esc or its UI button.
- Repeat casts: no magicka cost, daily limit, damage, visible effect or skill XP.
- Save/reload and start a new game: powers are present; saved favorites survive.
- Set one `Enabled=0`, reload, and confirm only that power is removed and its
  hotkey still works. Restore `1`, reload and confirm the power returns.
- Test one module alone and with a changed load order; disable its ESP and
  confirm its original hotkey still opens the panel.
- Test save changes/death reload and casting while another Prisma panel owns
  focus: no stale callback opens a view. Equipment enhancement still requires
  the existing workstation conditions; music panel still does not pause play.

Binary schema reference: [TES5Edit definitions](https://github.com/TES5Edit/TES5Edit/blob/dev-4.1.6/Core/wbDefinitionsTES5.pas).
