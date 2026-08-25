# Release layout

The final archive will have this layout:

```text
Follower Spellbook Manager/
├─ SKSE/plugins/FollowerSpellbookManager.dll
├─ SKSE/plugins/FollowerSpellbookManager.ini
└─ PrismaUI/views/FollowerSpellbookManager/
   ├─ index.html
   └─ assets/
```

Install the archive as a new MO2 mod, then enable it after Prisma UI. No ESP is required for the first release.

The INI file defaults to Shift+S and can be edited in the MO2 mod folder; restart Skyrim after changing it.
