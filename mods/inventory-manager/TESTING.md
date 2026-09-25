# Meridian prototype validation — 2026-09-13

## Completed

- `xmake build -y`: release DLL builds successfully with MSVC 2022, including `/utf-8`.
- `pnpm run build`: TypeScript and Vite production build pass.
- Browser manual checks: weapon preview fallback, keyboard D navigation to armor, magic page without preview, and independent details scrolling layout.
- Vendored ViewAPI, RenderLayerAPI and NifViewAPI hashes match the SDK bundled with the locally installed Meridian 1.5.0 runtime.
- Package and isolated MO2 test profile prepared with the original profile retained.

The desktop helper could not return the running MO2 main window as a targetable
window, including after a launch/refresh attempt. No game was launched by this
test, and no real NIF rendering, SKSE input, or load lifecycle result is claimed.

## In-game gate (not run)

Select **物品清单-Meridian测试** in MO2 and start Skyrim through SKSE.
Use the copied local save in that profile, then press **Shift+D**.

1. Select a vanilla sword, shield, and armor. Each should replace the icon with
   its inventory/world model. Drag, zoom and reset should work without equipping
   the item or moving the player.
2. Test one loose-file custom weapon and one BSA-backed model, including a texture
   replacer. Record any missing meshes, textures or unsupported materials.
3. Rapidly move between several weapons, switch to magic, then close/reopen.
   No stale model or checkerboard should remain over the page or gameplay.
4. Check search typing, Enter to equip, F to favorite, Alt page switching,
   hotkey rebinding, Escape and Shift+D closing. Activating the reset button
   with Enter must not equip the selected item.
5. Open a PrismaUI panel before attempting Shift+D. Inventory Manager should
   refuse to take focus. Test the reverse direction as well; other consumers
   may require their own cross-framework guard.
6. Load a save, return to the menu, and reopen the panel. Check for stale models,
   stuck pause, lost movement or stuck modifier keys. Test Alt-Tab restoration.
7. Repeat with the actual graphics stack (Community Shaders/ENB/upscaler if used),
   at the user's normal resolution. Confirm the model stays inside its viewport.

Look in `Documents/My Games/Skyrim Special Edition/SKSE` for InventoryManager
and Meridian logs, or the corresponding MO2 overwrite location. Preview requests
log their FormID and mesh path; failures should leave the normal item controls usable.
