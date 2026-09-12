"""Build four independent ESL-flagged ESPs; no game files or Python packages needed.

Binary layout: TES5Edit Core/wbDefinitionsTES5.pas (SPEL/SPIT and MGEF/DATA).
https://github.com/TES5Edit/TES5Edit/blob/dev-4.1.6/Core/wbDefinitionsTES5.pas
Local IDs 800/801 are permanent: changing them would break saved favorites.
"""
from pathlib import Path
import struct

ROOT = Path(__file__).resolve().parents[2]
MODULES = {
    "inventory-manager": ("InventoryManager", "打开物品管理"),
    "durability-manager": ("DurabilityManager", "打开装备维护"),
    "follower-spellbook-manager": ("FollowerSpellbookManager", "打开随从法术"),
    "music-manager": ("MusicManager", "打开音乐管理"),
}
SPELL_ID, EFFECT_ID = 0x01000800, 0x01000801


def sub(tag, data):
    return struct.pack("<4sH", tag, len(data)) + data


def z(text):
    return text.encode("utf-8") + b"\0"


def record(tag, form, data, flags=0):
    return struct.pack("<4sIIIIHH", tag, len(data), flags, form, 0, 44, 0) + data


def group(tag, data):
    return struct.pack("<4sI4siHHHH", b"GRUP", 24 + len(data), tag, 0, 0, 0, 0, 0) + data


def plugin(name, title):
    header = sub(b"HEDR", struct.pack("<fII", 1.7, 2, 0x802))
    header += sub(b"CNAM", z(name)) + sub(b"MAST", z("Skyrim.esm")) + sub(b"DATA", bytes(8))
    # Inert Script archetype, without VMAD: the DLL handles TESSpellCastEvent.
    # No hit events, duration, magnitude, area, visual effects or skill experience.
    effect = bytearray(152)
    struct.pack_into("<I", effect, 0, 0x0C008E10)
    for offset in (12, 16, 68, 88):
        struct.pack_into("<i", effect, offset, -1)  # no skill/resistance/actor values
    struct.pack_into("<I", effect, 64, 1)  # Script archetype
    struct.pack_into("<I", effect, 80, 1)  # Fire and Forget; Self delivery is zero
    struct.pack_into("<I", effect, 140, 2)  # Silent
    mgef = sub(b"EDID", z(name + "PanelEffect")) + sub(b"FULL", z(title))
    mgef += sub(b"DATA", effect) + sub(b"DNAM", z("打开管理面板。"))
    spell = sub(b"EDID", z(name + "PanelPower")) + sub(b"OBND", bytes(12))
    spell += sub(b"FULL", z(title)) + sub(b"ETYP", struct.pack("<I", 0x25BEE))  # Voice
    spell += sub(b"DESC", z("打开对应管理面板，可收藏。无魔法消耗，可重复使用。"))
    spell += sub(b"SPIT", struct.pack("<IIIfIIffI", 0, 0xB00001, 3, 0, 1, 0, 0, 0, 0))
    spell += sub(b"EFID", struct.pack("<I", EFFECT_ID)) + sub(b"EFIT", struct.pack("<fII", 0, 0, 0))
    return (record(b"TES4", 0, header, 0x200)
            + group(b"MGEF", record(b"MGEF", EFFECT_ID, mgef))
            + group(b"SPEL", record(b"SPEL", SPELL_ID, spell)))


if __name__ == "__main__":
    for folder, (name, title) in MODULES.items():
        path = ROOT / "mods" / folder / "packaging" / (name + ".esp")
        path.write_bytes(plugin(name, title))
        print(path.relative_to(ROOT))
