# Arcane Armory release requirements

- Preserve Chinese names and user-approved geometric designs. Concepts first when requested; implement only after approval.
- Keep existing reduced emission. Active weapons currently use base damage 90 and weapon Speed 1.5.
- Preserve plugin name `ArcaneArsenal.esp`, ESL flag, Skyrim SE 1.5.97 compatibility, and all existing FormIDs. Never reuse retired IDs; 0x90C–0x918 includes the retired crystal test chest.
- For every newly added weapon, update the user's existing SPID file as part of delivery:
  `C:/Users/linos/Desktop/games/+skyrim/MO2/mods/功能模组-物品分发-SPID+CID配置-🟪🟨/-item_DISTR.ini`.
  The filename is `-item_DISTR.ini`, not a subdirectory `-item/_DISTR.ini`.
- Use the existing rule format `Item = <EditorID>|NONE|NONE|NONE|NONE|1|0.01`. Keep the literal chance value `0.01`; do not reinterpret it as `1` or alter other weapons' filters/probabilities. Do not switch Item to DeathItem without a user request.
- Back up the external SPID file before modifying it, avoid duplicate rules, verify EditorIDs against the built plugin, and preserve unrelated contents and encoding/newlines. Use the project SPID sync helper when available.
- Package and update the existing MO2 installation with visible version metadata and backups. Do not kill the running game. Build/verify/package first if installation must wait for it to close.
- Scope changes to this mod; unrelated workspace mods may be under active development. Commit or push only when requested.
