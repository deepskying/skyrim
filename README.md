# Follower Spellbook Manager

An SKSE + Prisma UI mod for Skyrim Special Edition 1.5.97. It lets the player inspect loaded followers' spells and teach them spell tomes from the player's inventory.

## Current behavior

- Press **F10** to open or close the panel.
- Click the close button or press **Esc** to close the panel from any page.
- Open to a grid of loaded player teammates, then open one follower's detail page.
- The responsive panel uses 90% of the available viewport and a translucent blue-green theme.
- View that follower's castable spells in an independently scrolling grid, with each card showing the calculated cost and its share of the follower's maximum magicka.
- Filter the list by magic school.
- Select a spell tome from the player's inventory and teach it to the selected follower.
- The tome is removed only after `Actor::AddSpell` succeeds.
- Each successful teaching is also stored in the SKSE co-save. On a later load, the plugin resolves the saved FormIDs and reapplies any tracked spell that a current player teammate is missing.

## Runtime requirements

- Skyrim SE 1.5.97 and the matching SKSE64 build
- Address Library for SKSE Plugins
- Media Keys Fix SKSE
- Prisma UI

The current MO2 profile already contains these requirements. The mod is deliberately not copied into MO2 until its native DLL has compiled and been tested.

## Build

1. Ensure the `reference/` directory contains the Prisma UI example repositories and their submodules.
2. In `web/`, run `npm install` followed by `npm run build`.
3. In `native/`, run `xmake build -y`.

The web build produces the Prisma view. The native build produces the SKSE plugin DLL. A later packaging step combines them under the MO2 mod directory structure.
