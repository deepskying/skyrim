"""Resolve the active MO2 load order and read every WEAP record in it.

The result is one entry per weapon FormID holding the *effective* values, i.e.
the record as the game would see it after every override has been applied.
"""
from __future__ import annotations

import configparser
import hashlib
import json
import os
import struct
import time
from pathlib import Path

import esp

OFFICIAL = (
    "skyrim.esm",
    "update.esm",
    "dawnguard.esm",
    "hearthfires.esm",
    "dragonborn.esm",
)

# Bump this whenever the shape of a weapon entry changes, so that stale JSON
# caches written by an older version are discarded instead of silently reused.
SCHEMA = 2

# Categories follow the WEAP animation type, which is the field the game uses
# to pick attack animations. Two-handed axes, warhammers and scythes all share
# animation type 6 (TwoHandAxe), so they live in one category by design.
CATEGORIES = [
    {"key": "sword", "label": "单手剑", "anim": 1},
    {"key": "dagger", "label": "匕首", "anim": 2},
    {"key": "waraxe", "label": "单手斧", "anim": 3},
    {"key": "mace", "label": "单手钉锤", "anim": 4},
    {"key": "greatsword", "label": "双手剑", "anim": 5},
    {"key": "twohandaxe", "label": "双手斧类", "anim": 6},
    {"key": "bow", "label": "弓", "anim": 7},
    {"key": "staff", "label": "法杖", "anim": 8},
    {"key": "crossbow", "label": "弩", "anim": 9},
    {"key": "other", "label": "其他", "anim": 0},
]
CATEGORY_BY_ANIM = {item["anim"]: item["key"] for item in CATEGORIES}
CATEGORY_LABELS = {item["key"]: item["label"] for item in CATEGORIES}

# Vanilla ceilings measured from the user's own masters, kept here as the
# default suggestion for the per-category damage cap.
VANILLA_CEILING = {
    "sword": 14,
    "dagger": 11,
    "waraxe": 15,
    "mace": 16,
    "greatsword": 24,
    "twohandaxe": 27,
    "bow": 19,
    "staff": 27,
    "crossbow": 22,
    "other": 15,
}
VANILLA_SPEED = {
    "sword": 1.0,
    "dagger": 1.3,
    "waraxe": 0.9,
    "mace": 0.8,
    "greatsword": 0.7,
    "twohandaxe": 0.6,
    "bow": 0.5,
    "staff": 1.0,
    "crossbow": 1.0,
    "other": 1.0,
}


def _clean(value: str) -> str:
    return value.strip()


def profile_paths(mo2_dir: Path, profile: str | None) -> dict:
    """Locate the profile's modlist/plugins/loadorder and the game data folder."""
    mo2_dir = Path(mo2_dir)
    if profile is None:
        ini = mo2_dir / "ModOrganizer.ini"
        profile = "-std-"
        if ini.exists():
            for line in ini.read_text(encoding="utf-8", errors="replace").splitlines():
                if line.startswith("selected_profile="):
                    profile = line.split("=", 1)[1].strip().lstrip("@ByteArray(").rstrip(")")
                    break
    profile_dir = mo2_dir / "profiles" / profile
    if not profile_dir.exists():
        raise FileNotFoundError(f"profile folder not found: {profile_dir}")
    return {
        "profile": profile,
        "profile_dir": profile_dir,
        "mods_dir": mo2_dir / "mods",
        "plugins": profile_dir / "plugins.txt",
        "loadorder": profile_dir / "loadorder.txt",
        "modlist": profile_dir / "modlist.txt",
        "skyrim_ini": profile_dir / "skyrim.ini",
    }


def _read_lines(path: Path) -> list[str]:
    if not path.exists():
        return []
    return [
        _clean(line)
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines()
        if _clean(line) and not _clean(line).startswith("#")
    ]


def mod_priority(modlist: Path) -> dict[str, int]:
    """Mod name -> priority index, smaller wins (MO2 writes highest first)."""
    priority: dict[str, int] = {}
    for index, line in enumerate(_read_lines(modlist)):
        name = line[1:] if line[0] in "+-*" else line
        priority.setdefault(name, index)
    return priority


def plugin_index(mods_dir: Path, data_dir: Path, priority: dict[str, int]) -> dict[str, Path]:
    """Map ``plugin name lowercased`` -> the winning file path."""
    candidates: dict[str, list[tuple[int, Path]]] = {}
    if mods_dir.exists():
        for raw_root, _dirs, files in os.walk(mods_dir):
            root = Path(raw_root)
            for name in files:
                if name.lower().endswith((".esp", ".esm", ".esl")):
                    mod = root.relative_to(mods_dir).parts[0] if root != mods_dir else ""
                    candidates.setdefault(name.lower(), []).append(
                        (priority.get(mod, 10**9), root / name)
                    )
    if data_dir.exists():
        for path in data_dir.iterdir():
            if path.is_file() and path.suffix.lower() in (".esp", ".esm", ".esl"):
                candidates.setdefault(path.name.lower(), []).append((10**9 + 1, path))
    index: dict[str, Path] = {}
    for name, items in candidates.items():
        index[name] = sorted(items, key=lambda item: (item[0], str(item[1])))[0][1]
    return index


def mod_of(path: Path, mods_dir: Path, data_dir: Path) -> str:
    """Return the MO2 mod folder a plugin file lives in (or the game itself)."""
    try:
        relative = Path(path).resolve().relative_to(Path(mods_dir).resolve())
        return relative.parts[0] if relative.parts else "(未分类)"
    except (ValueError, OSError):
        pass
    try:
        if Path(path).resolve().parent == Path(data_dir).resolve():
            return "(游戏本体 Data)"
    except OSError:
        pass
    return "(未知来源)"


def load_order(paths: dict, index: dict[str, Path]) -> tuple[list[str], list[str]]:
    """Return ``(ordered plugin names, enabled plugin names)``."""
    order = _read_lines(paths["loadorder"]) or _read_lines(paths["plugins"])
    entries = _read_lines(paths["plugins"]) or order
    enabled = {line[1:].lower() for line in entries if line.startswith("*")}
    if not enabled:
        enabled = {name.lower() for name in entries} | set(OFFICIAL)
    ordered: list[str] = []
    seen: set[str] = set()
    for name in list(OFFICIAL) + order:
        key = name.lower()
        if key in seen or key not in index:
            continue
        if key not in enabled and key not in OFFICIAL:
            continue
        seen.add(key)
        ordered.append(name)
    for name in entries:
        key = name.lstrip("*").lower()
        if key in seen or key not in index or key not in enabled:
            continue
        seen.add(key)
        ordered.append(name.lstrip("*"))
    return ordered, sorted(enabled)


def game_language(skyrim_ini: Path) -> str:
    if not skyrim_ini.exists():
        return "english"
    parser = configparser.ConfigParser(strict=False)
    try:
        parser.read(skyrim_ini, encoding="utf-8")
        return parser.get("General", "sLanguage", fallback="english").strip().lower()
    except Exception:
        return "english"


class StringTables:
    """Resolve localized FULL string ids from ``Data/Strings/*.STRINGS``."""

    def __init__(self, data_dir: Path, language: str):
        self.directory = Path(data_dir) / "Strings"
        self.language = language
        self._files: dict[str, Path] = {}
        self._cache: dict[str, dict[int, str]] = {}
        if self.directory.exists():
            for path in self.directory.iterdir():
                if path.suffix.lower() == ".strings":
                    self._files[path.name.lower()] = path

    def table(self, plugin: str) -> dict[int, str]:
        stem = Path(plugin).stem.lower()
        if stem in self._cache:
            return self._cache[stem]
        path = self._files.get(f"{stem}_{self.language}.strings")
        if path is None:
            path = self._files.get(f"{stem}_english.strings")
        if path is None:
            for name, candidate in self._files.items():
                if name.startswith(f"{stem}_"):
                    path = candidate
                    break
        table: dict[int, str] = {}
        if path is not None:
            try:
                table = esp.load_string_table(path)
            except Exception:
                table = {}
        self._cache[stem] = table
        return table


def _f32(data: bytes, offset: int) -> float | None:
    if len(data) < offset + 4:
        return None
    return struct.unpack_from("<f", data, offset)[0]


def _u16(data: bytes, offset: int) -> int | None:
    if len(data) < offset + 2:
        return None
    return struct.unpack_from("<H", data, offset)[0]


def _u32(data: bytes, offset: int) -> int | None:
    if len(data) < offset + 4:
        return None
    return struct.unpack_from("<I", data, offset)[0]


def _i32(data: bytes, offset: int) -> int | None:
    if len(data) < offset + 4:
        return None
    return struct.unpack_from("<i", data, offset)[0]


def weapon_fields(subs: dict[bytes, bytes]) -> dict:
    """Pull the fields the balancer cares about out of a merged subrecord map."""
    out: dict = {
        "damage": None,
        "weight": None,
        "value": None,
        "speed": None,
        "reach": None,
        "stagger": None,
        "anim": None,
        "dnam_flags": None,
        "flags2": None,
        "anim_mult": None,
        "skill": None,
        "vats": None,
        "projectiles": None,
        "crit": None,
        "crit_mult": None,
        "enchantment": None,
        "template": None,
        "etyp": None,
        "keywords": [],
        "full": None,
    }
    data = subs.get(b"DATA")
    if data:
        if len(data) >= 4:
            out["value"] = _u32(data, 0)
        out["weight"] = _f32(data, 4)
        out["damage"] = _u16(data, 8)
    dnam = subs.get(b"DNAM")
    if dnam:
        if len(dnam) >= 1:
            out["anim"] = dnam[0]
        out["speed"] = _f32(dnam, 4)
        out["reach"] = _f32(dnam, 8)
        out["dnam_flags"] = _u16(dnam, 12)
        out["vats"] = dnam[24] if len(dnam) > 24 else None
        out["projectiles"] = dnam[26] if len(dnam) > 26 else None
        out["flags2"] = _u32(dnam, 40)
        out["anim_mult"] = _f32(dnam, 44)
        out["skill"] = _i32(dnam, 76)
        out["stagger"] = _f32(dnam, 96)
    crdt = subs.get(b"CRDT")
    if crdt:
        out["crit"] = _u16(crdt, 0)
        out["crit_mult"] = _f32(crdt, 4)
    if b"EITM" in subs:
        out["enchantment"] = _u32(subs[b"EITM"], 0)
    if b"CNAM" in subs:
        out["template"] = _u32(subs[b"CNAM"], 0)
    if b"ETYP" in subs:
        out["etyp"] = _u32(subs[b"ETYP"], 0)
    kwda = subs.get(b"KWDA")
    if kwda:
        out["keywords"] = [
            struct.unpack_from("<I", kwda, index)[0]
            for index in range(0, len(kwda) - 3, 4)
        ]
    out["full"] = subs.get(b"FULL")
    return out


def _round(value, digits=4):
    return None if value is None else round(value, digits)


def compute_signature(index: dict[str, Path], ordered: list[str]) -> str:
    """Hash the identity of every plugin in the load order (name + mtime)."""
    payload = []
    for name in ordered:
        path = index[name.lower()]
        try:
            stat = path.stat()
            payload.append([name, str(path), int(stat.st_mtime), stat.st_size])
        except OSError:
            payload.append([name, str(path), 0, 0])
    return hashlib.sha1(json.dumps(payload, ensure_ascii=False).encode("utf-8")).hexdigest()


def scan_cached(config: dict, cache_path: Path, progress=None) -> dict:
    """Return the catalogue, reusing the JSON cache while the load order holds."""
    paths = profile_paths(Path(config["mo2_dir"]), config.get("profile"))
    data_dir = Path(config["data_dir"])
    index = plugin_index(paths["mods_dir"], data_dir, mod_priority(paths["modlist"]))
    ordered, _enabled = load_order(paths, index)
    signature = compute_signature(index, ordered)
    if cache_path.exists():
        try:
            cached = json.loads(cache_path.read_text(encoding="utf-8"))
            if (
                cached.get("schema") == SCHEMA
                and cached.get("signature") == signature
                and cached.get("weapons")
            ):
                cached["from_cache"] = True
                return cached
        except Exception:
            pass
    result = scan(config, progress)
    result["from_cache"] = False
    try:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
    except OSError:
        pass
    return result


def scan(config: dict, progress=None) -> dict:
    """Read the whole load order and return the weapon catalogue."""
    started = time.time()
    paths = profile_paths(Path(config["mo2_dir"]), config.get("profile"))
    data_dir = Path(config["data_dir"])
    priority = mod_priority(paths["modlist"])
    index = plugin_index(paths["mods_dir"], data_dir, priority)
    ordered, enabled = load_order(paths, index)
    if not ordered:
        raise RuntimeError("no plugins resolved - check the MO2 path and profile")
    language = game_language(paths["skyrim_ini"])
    strings = StringTables(data_dir, language)
    mod_names = {
        name.lower(): mod_of(index[name.lower()], paths["mods_dir"], data_dir) for name in ordered
    }

    contributions: dict[tuple[str, int], list[tuple]] = {}
    keyword_edid: dict[tuple[str, int], str] = {}
    plugin_meta: dict[str, dict] = {}
    failures: list[dict] = []
    for order, name in enumerate(ordered):
        path = index[name.lower()]
        try:
            header = esp.read_header(path)
        except Exception as error:  # pragma: no cover - defensive
            failures.append({"plugin": name, "error": str(error)})
            continue
        masters = [master.lower() for master in header["masters"]]
        plugin_meta[name.lower()] = {
            "name": name,
            "path": str(path),
            "localized": header["localized"],
            "masters": masters,
            "order": order,
        }
        try:
            data = path.read_bytes()
            for sig, form, flags, _version, payload in esp.iter_records(data, {b"WEAP", b"KYWD"}):
                master_index = form >> 24
                object_id = form & 0xFFFFFF
                if master_index < len(masters):
                    owner = masters[master_index]
                else:
                    owner = name.lower()
                if sig == b"KYWD":
                    edid = ""
                    for key, value in esp.iter_subrecords(payload):
                        if key == b"EDID":
                            edid = esp.decode_text(value)
                            break
                    if edid:
                        keyword_edid.setdefault((owner, object_id), edid)
                    continue
                subs = {}
                for key, value in esp.iter_subrecords(payload):
                    subs[key] = value
                contributions.setdefault((owner, object_id), []).append(
                    (order, name, header["localized"], subs, flags)
                )
        except Exception as error:  # pragma: no cover - defensive
            failures.append({"plugin": name, "error": f"{type(error).__name__}: {error}"})
        if progress is not None and order % 50 == 0:
            progress(order, len(ordered), name)

    weapons: list[dict] = []
    for (owner, object_id), items in contributions.items():
        items.sort(key=lambda item: item[0])
        merged: dict[bytes, bytes] = {}
        full_owner = None
        for _order, plugin, _localized, subs, _flags in items:
            merged.update(subs)
            if b"FULL" in subs:
                full_owner = plugin
        fields = weapon_fields(merged)
        last = items[-1]
        winner = last[1]
        flags = 0
        for item in items:
            flags = item[4]

        edid = ""
        raw_edid = merged.get(b"EDID")
        if raw_edid:
            edid = esp.decode_text(raw_edid)

        name = edid
        if fields["full"]:
            provider = (full_owner or winner).lower()
            if plugin_meta.get(provider, {}).get("localized"):
                string_id = _u32(fields["full"], 0)
                if string_id is not None:
                    name = strings.table(provider).get(string_id) or edid
            else:
                name = esp.lstring(fields["full"]) or edid

        keywords: list[str] = []
        for form in fields["keywords"]:
            master_index = form >> 24
            masters = plugin_meta.get(winner.lower(), {}).get("masters", [])
            source = masters[master_index] if master_index < len(masters) else winner.lower()
            keywords.append(keyword_edid.get((source, form & 0xFFFFFF), f"{form:08X}"))

        category = CATEGORY_BY_ANIM.get(fields["anim"], "other")
        source_kind = "vanilla" if owner in OFFICIAL else "mod"
        owner_name = plugin_meta.get(owner, {}).get("name", owner)
        winner_name = plugin_meta.get(winner.lower(), {}).get("name", winner)
        weapons.append(
            {
                "key": f"{owner}:{object_id:06X}",
                "formid": f"{object_id:06X}",
                "owner": owner,
                "owner_name": owner_name,
                "mod": mod_names.get(owner, owner_name),
                "winner": winner,
                "winner_name": winner_name,
                "winner_mod": mod_names.get(winner.lower(), winner_name),
                "source": source_kind,
                "overridden": winner.lower() != owner,
                "edid": edid,
                "name": name,
                "category": category,
                "anim": fields["anim"],
                "damage": fields["damage"],
                "speed": _round(fields["speed"]),
                "weight": _round(fields["weight"], 2),
                "value": fields["value"],
                "reach": _round(fields["reach"], 2),
                "stagger": _round(fields["stagger"], 2),
                "crit": fields["crit"],
                "crit_mult": _round(fields["crit_mult"], 2),
                "anim_mult": _round(fields["anim_mult"], 4),
                "skill": fields["skill"],
                "projectiles": fields["projectiles"],
                "etyp": f"{fields['etyp']:08X}" if fields["etyp"] else None,
                "keywords": keywords,
                "enchanted": fields["enchantment"] is not None,
                "enchantment": f"{fields['enchantment']:08X}" if fields["enchantment"] else None,
                "non_playable": bool(flags & esp.NON_PLAYABLE),
                "flags2": fields["flags2"],
                "dnam_flags": fields["dnam_flags"],
            }
        )

    weapons.sort(key=lambda item: (item["category"], -(item["damage"] or 0), item["edid"]))
    signature = compute_signature(index, ordered)
    return {
        "schema": SCHEMA,
        "signature": signature,
        "generated": time.strftime("%Y-%m-%d %H:%M:%S"),
        "elapsed": round(time.time() - started, 2),
        "profile": paths["profile"],
        "language": language,
                "plugins": [
                    {
                        "name": name,
                        "path": str(index[name.lower()]),
                        "mod": mod_names.get(name.lower(), ""),
                        "masters": len(plugin_meta.get(name.lower(), {}).get("masters", [])),
                    }
            for name in ordered
        ],
        "plugin_count": len(ordered),
        "enabled_count": len(enabled),
        "failure_count": len(failures),
        "failures": failures[:20],
        "weapons": weapons,
    }
