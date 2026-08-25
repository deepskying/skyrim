# Follower Spellbook Manager

## First release

This project targets Skyrim Special Edition runtime 1.5.97 with SKSE64 and Prisma UI.

The native SKSE plugin owns the game data bridge. It finds loaded player teammates, reads their learned spells, reads spell tomes from the player's inventory, and applies confirmed learning requests. The Prisma UI view renders the management panel and sends typed JSON actions back to the plugin.

## Safety rules

- Only loaded actors marked as player teammates are selectable.
- Only book tomes that teach a spell are offered.
- A tome is consumed only after the selected follower successfully receives its spell.
- The first release does not expose spell removal.

## Interaction

F10 opens or closes the panel. The game pauses while the panel has focus.
