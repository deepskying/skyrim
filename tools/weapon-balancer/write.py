"""Build the ESL-flagged override patch described by a change plan.

The patch contains nothing but complete copies of the records it needs to
change, so the game sees the original weapon with a different damage, speed or
critical damage and nothing else. Every FormID inside a copied record is
rewritten from the source plugin's master list into the patch's own master
list; records that carry structures this tool cannot translate safely (script
data, destructible data, alternate textures) are skipped and reported instead
of being written half-correct.
"""
from __future__ import annotations

import struct
import time
from pathlib import Path

import esp
import scan

HEDR = struct.Struct("<fII")
RECORD_HEADER = struct.Struct("<4sIIIIHH")

# Subrecords that never contain FormIDs and can be copied verbatim.
SAFE_PASSTHROUGH = {
    b"EDID",
    b"OBND",
    b"MODL",
    b"MODT",
    b"MODB",
    b"FULL",
    b"ICON",
    b"ICO2",
    b"DESC",
    b"MOD3",
    b"MO3T",
    b"NNAM",
    b"EAMT",
    b"KSIZ",
    b"VNAM",
    b"DMDT",
    b"DATA",
    b"DNAM",
}

# One FormID in the subrecord payload.
FORMID_SINGLE = {
    b"EITM",
    b"ETYP",
    b"BIDS",
    b"BAMT",
    b"YNAM",
    b"ZNAM",
    b"INAM",
    b"WNAM",
    b"SNAM",
    b"XNAM",
    b"NAM7",
    b"TNAM",
    b"UNAM",
    b"NAM9",
    b"NAM8",
    b"CNAM",
}
# A list of FormIDs.
FORMID_LIST = {b"KWDA"}
# FormID inside a fixed layout: subrecord -> byte offset.
FORMID_OFFSET = {b"CRDT": 16}
# Anything else is treated as untranslatable and the record is skipped.


class Record:
    """One WEAP record collected from one plugin."""

    __slots__ = ("order", "plugin", "masters", "subrecords", "flags", "version")

    def __init__(self, order, plugin, masters, subrecords, flags, version):
        self.order = order
        self.plugin = plugin
        self.masters = masters
        self.subrecords = subrecords
        self.flags = flags
        self.version = version


def collect(config: dict, targets: set[tuple[str, int]]) -> dict:
    """Read every load-order plugin and keep the raw records for ``targets``.

    ``targets`` holds ``(owner plugin lowercased, object id)`` pairs.
    """
    paths = scan.profile_paths(Path(config["mo2_dir"]), config.get("profile"))
    data_dir = Path(config["data_dir"])
    index = scan.plugin_index(paths["mods_dir"], data_dir, scan.mod_priority(paths["modlist"]))
    ordered, _enabled = scan.load_order(paths, index)
    contributions: dict[tuple[str, int], list[Record]] = {}
    masters_of: dict[str, list[str]] = {}
    failures: list[dict] = []
    for order, name in enumerate(ordered):
        path = index[name.lower()]
        try:
            header = esp.read_header(path)
            masters = [master.lower() for master in header["masters"]]
            masters_of[name.lower()] = masters
            data = path.read_bytes()
            for sig, form, flags, version, payload in esp.iter_records(data, {b"WEAP"}):
                master_index = form >> 24
                object_id = form & 0xFFFFFF
                owner = masters[master_index] if master_index < len(masters) else name.lower()
                key = (owner, object_id)
                if key not in targets:
                    continue
                contributions.setdefault(key, []).append(
                    Record(
                        order,
                        name.lower(),
                        masters,
                        [(sub_sig, value) for sub_sig, value in esp.iter_subrecords(payload)],
                        flags,
                        version,
                    )
                )
        except Exception as error:  # pragma: no cover - defensive
            failures.append({"plugin": name, "error": f"{type(error).__name__}: {error}"})
    for items in contributions.values():
        items.sort(key=lambda record: record.order)
    return {
        "contributions": contributions,
        "masters_of": masters_of,
        "order": ordered,
        "index": index,
        "failures": failures,
    }


def _formid_plugin(form_id: int, record: Record):
    master_index = form_id >> 24
    if master_index < len(record.masters):
        return record.masters[master_index], form_id & 0xFFFFFF
    return record.plugin, form_id & 0xFFFFFF


def _referenced(record: Record) -> set[str]:
    """Which plugins this record points at (for the patch master list)."""
    found: set[str] = set()
    for sig, value in record.subrecords:
        if sig in FORMID_SINGLE and len(value) >= 4:
            form = struct.unpack_from("<I", value, 0)[0]
            if form:
                found.add(_formid_plugin(form, record)[0])
        elif sig in FORMID_LIST:
            for offset in range(0, len(value) - 3, 4):
                form = struct.unpack_from("<I", value, offset)[0]
                if form:
                    found.add(_formid_plugin(form, record)[0])
        elif sig in FORMID_OFFSET and len(value) >= FORMID_OFFSET[sig] + 4:
            form = struct.unpack_from("<I", value, FORMID_OFFSET[sig])[0]
            if form:
                found.add(_formid_plugin(form, record)[0])
    return found


def _translate(value: bytes, record: Record, patch_index: dict[str, int]) -> bytes:
    """Rewrite the FormID of a single-reference subrecord into the patch index.

    Self references (the high byte is the source plugin's own index) must be
    translated too, so ``_formid_plugin`` is used instead of assuming the high
    byte is a master index.
    """
    if len(value) < 4:
        return value
    form = struct.unpack_from("<I", value, 0)[0]
    if not form:
        return value
    source, object_id = _formid_plugin(form, record)
    index = patch_index.get(source)
    if index is None:
        raise KeyError(source)
    return struct.pack("<I", (index << 24) | object_id) + value[4:]


def _translate_many(value: bytes, record: Record, patch_index: dict[str, int]) -> bytes:
    out = bytearray(value)
    for offset in range(0, len(value) - 3, 4):
        form = struct.unpack_from("<I", value, offset)[0]
        if not form:
            continue
        source, object_id = _formid_plugin(form, record)
        index = patch_index.get(source)
        if index is None:
            raise KeyError(source)
        struct.pack_into("<I", out, offset, (index << 24) | object_id)
    return bytes(out)


def _translate_offset(value: bytes, record: Record, patch_index: dict[str, int], offset: int) -> bytes:
    if len(value) < offset + 4:
        return value
    form = struct.unpack_from("<I", value, offset)[0]
    if not form:
        return value
    source, object_id = _formid_plugin(form, record)
    index = patch_index.get(source)
    if index is None:
        raise KeyError(source)
    out = bytearray(value)
    struct.pack_into("<I", out, offset, (index << 24) | object_id)
    return bytes(out)


def _merge(records: list[Record], patch_index: dict[str, int]) -> tuple[list[bytes], dict[bytes, bytes]]:
    """Apply override semantics: later load-order plugins win per subrecord."""
    order: list[bytes] = []
    merged: dict[bytes, bytes] = {}
    for record in records:
        for sig, value in record.subrecords:
            if sig in FORMID_SINGLE:
                value = _translate(value, record, patch_index)
            elif sig in FORMID_LIST:
                value = _translate_many(value, record, patch_index)
            elif sig in FORMID_OFFSET:
                value = _translate_offset(value, record, patch_index, FORMID_OFFSET[sig])
            if sig not in merged:
                order.append(sig)
            merged[sig] = value
    return order, merged


def _encode_subrecord(sig: bytes, value: bytes) -> bytes:
    if len(value) > 0xFFFF:
        return b"XXXX" + struct.pack("<H", 4) + struct.pack("<I", len(value)) + sig + struct.pack("<H", 0) + value
    return sig + struct.pack("<H", len(value)) + value


def _write_payload(order: list[bytes], merged: dict[bytes, bytes], change: dict) -> bytes:
    """Apply the planned values on top of the merged record."""
    data = merged.get(b"DATA")
    if data and len(data) >= 10 and change["after"]["damage"] is not None:
        buffer = bytearray(data)
        struct.pack_into("<H", buffer, 8, int(change["after"]["damage"]))
        merged[b"DATA"] = bytes(buffer)
    dnam = merged.get(b"DNAM")
    if dnam:
        buffer = bytearray(dnam)
        if len(buffer) >= 8 and change["after"]["speed"] is not None:
            struct.pack_into("<f", buffer, 4, float(change["after"]["speed"]))
        if len(buffer) >= 48 and change["after"]["anim_mult"] is not None:
            struct.pack_into("<f", buffer, 44, float(change["after"]["anim_mult"]))
        merged[b"DNAM"] = bytes(buffer)
    crdt = merged.get(b"CRDT")
    if crdt and len(crdt) >= 2 and change["after"].get("crit") is not None:
        buffer = bytearray(crdt)
        struct.pack_into("<H", buffer, 0, int(change["after"]["crit"]))
        merged[b"CRDT"] = bytes(buffer)
    return b"".join(_encode_subrecord(sig, merged[sig]) for sig in order)


def build(config: dict, plan: dict, mod_name: str = "武器平衡-WeaponRebalance", plugin_name: str = "WeaponRebalance.esp") -> dict:
    """Create the patch plugin file and return a report."""
    changes = [change for change in plan["changes"]]
    targets = set()
    for change in changes:
        owner, object_id = change["key"].rsplit(":", 1)
        targets.add((owner, int(object_id, 16)))

    collected = collect(config, targets)
    contributions = collected["contributions"]
    order_of = {name.lower(): index for index, name in enumerate(collected["order"])}

    skipped: list[dict] = []
    usable: list[tuple[dict, list[Record]]] = []
    referenced: set[str] = set()
    for change in changes:
        owner, object_id = change["key"].rsplit(":", 1)
        records = contributions.get((owner, int(object_id, 16)))
        if not records:
            skipped.append({"edid": change["edid"], "reason": "找不到原始记录"})
            continue
        untranslatable = sorted(
            {
                sig.decode("ascii", "replace")
                for record in records
                for sig, _value in record.subrecords
                if sig not in SAFE_PASSTHROUGH and sig not in FORMID_SINGLE and sig not in FORMID_LIST and sig not in FORMID_OFFSET
            }
        )
        if untranslatable:
            skipped.append(
                {"edid": change["edid"], "reason": "含无法安全转换的子记录: " + ", ".join(untranslatable)}
            )
            continue
        if any(record.flags & 0x20 for record in records):
            skipped.append({"edid": change["edid"], "reason": "记录被标记为已删除"})
            continue
        # The plugin that owns the record must be a master of the patch, even
        # when none of the record's own subrecords point back at it.
        referenced.add(owner)
        for record in records:
            referenced |= _referenced(record)
        usable.append((change, records))

    masters = [name for name in collected["order"] if name.lower() in referenced]
    missing = sorted(referenced - {name.lower() for name in masters})
    if missing:
        skipped.extend({"edid": "", "reason": f"缺少主文件: {name}"} for name in missing)
    if len(masters) > 250:
        raise RuntimeError(f"补丁需要 {len(masters)} 个 master，超过上限，请分批生成")
    patch_index = {name.lower(): index for index, name in enumerate(masters)}

    records: list[bytes] = []
    written: list[dict] = []
    for change, records_in in usable:
        owner, object_id = change["key"].rsplit(":", 1)
        object_id = int(object_id, 16)
        index = patch_index.get(owner)
        if index is None:
            skipped.append({"edid": change["edid"], "reason": "记录所有者不在 master 列表"})
            continue
        try:
            sub_order, merged = _merge(records_in, patch_index)
        except KeyError as error:
            skipped.append({"edid": change["edid"], "reason": f"缺少主文件引用: {error.args[0]}"})
            continue
        payload = _write_payload(sub_order, merged, change)
        last = records_in[-1]
        flags = last.flags & ~esp.COMPRESSED & ~0x20
        records.append(
            RECORD_HEADER.pack(b"WEAP", len(payload), flags, (index << 24) | object_id, 0, last.version or 44, 0)
            + payload
        )
        written.append(
            {
                "edid": change["edid"],
                "name": change["name"],
                "formid": f"{index:02X}{object_id:06X}",
                "damage": change["after"]["damage"],
                "speed": change["after"]["speed"],
            }
        )

    body = b"".join(records)
    if body:
        # Records live in a top-level WEAP group, as every other plugin does.
        body = (
            struct.pack("<4sI4siHHHH", b"GRUP", len(body) + 24, b"WEAP", 0, 0, 0, 0, 0)
            + body
        )
    header = _header(masters, len(records), collected["index"])
    blob = header + body

    target_dir = Path(config["mo2_dir"]) / "mods" / mod_name
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / plugin_name
    if target.exists():
        backup = target.with_suffix(f".esp.bak-{time.strftime('%Y%m%d-%H%M%S')}")
        target.replace(backup)
    else:
        backup = None
    target.write_bytes(blob)
    _write_meta(target_dir, len(records), time.strftime("%Y-%m-%d %H:%M"))
    report = {
        "ok": True,
        "path": str(target),
        "mod_dir": str(target_dir),
        "backup": str(backup) if backup else None,
        "size": len(blob),
        "records": len(records),
        "masters": masters,
        "written": written,
        "skipped": skipped,
        "collect_failures": collected["failures"],
    }
    report["verify"] = verify(target, plan, written)
    return report


def _header(masters: list[str], record_count: int, index: dict[str, Path]) -> bytes:
    """Assemble a TES4 header record with an ESL flag and the master list."""
    entries = []
    for name in masters:
        path = index.get(name.lower())
        size = path.stat().st_size if path and path.exists() else 0
        value = name.encode("utf-8") + b"\0"
        entries.append(b"MAST" + struct.pack("<H", len(value)) + value)
        entries.append(b"DATA" + struct.pack("<H", 8) + struct.pack("<q", size))
    author = b"weapon-balancer" + b"\0"
    description = (
        "Weapon damage/speed normalisation patch generated by tools/weapon-balancer. "
        "Load it after the weapon mods it overrides."
    ).encode("utf-8") + b"\0"
    entries.append(b"CNAM" + struct.pack("<H", len(author)) + author)
    entries.append(b"SNAM" + struct.pack("<H", len(description)) + description)
    hedr = b"HEDR" + struct.pack("<H", 12) + HEDR.pack(1.7, record_count, 0x800)
    payload = hedr + b"".join(entries)
    return RECORD_HEADER.pack(b"TES4", len(payload), 0x200, 0, 0, 44, 0) + payload


def _write_meta(target_dir: Path, records: int, stamp: str) -> None:
    meta = target_dir / "meta.ini"
    meta.write_text(
        "[General]\n"
        "gameName=SkyrimSE\n"
        "modid=0\n"
        "version=1.0.0\n"
        "category=0\n"
        "repository=Local\n"
        f"comments=武器伤害/攻速规范化补丁，共 {records} 条记录覆盖。生成时间 {stamp}。\n",
        encoding="utf-8",
    )


def verify(patch_path: Path, plan: dict, written: list[dict] | None = None) -> dict:
    """Re-read the patch and confirm every planned value landed in it."""
    data = Path(patch_path).read_bytes()
    header = esp.read_header(Path(patch_path))
    masters = [name.lower() for name in header["masters"]]
    found: dict[tuple[int, int], dict] = {}
    for sig, form, _flags, _version, payload in esp.iter_records(data, {b"WEAP"}):
        merged: dict[bytes, bytes] = {}
        for sub_sig, value in esp.iter_subrecords(payload):
            merged[sub_sig] = value
        damage = struct.unpack_from("<H", merged[b"DATA"], 8)[0] if b"DATA" in merged else None
        speed = struct.unpack_from("<f", merged[b"DNAM"], 4)[0] if b"DNAM" in merged else None
        crit = struct.unpack_from("<H", merged[b"CRDT"], 0)[0] if b"CRDT" in merged else None
        found[(form >> 24, form & 0xFFFFFF)] = {"damage": damage, "speed": speed, "crit": crit}
    written_keys = set()
    for item in written or []:
        form = int(item["formid"], 16)
        written_keys.add((form >> 24, form & 0xFFFFFF))
    problems: list[str] = []
    checked = 0
    for change in plan["changes"]:
        owner, object_id = change["key"].rsplit(":", 1)
        object_id = int(object_id, 16)
        owner_index = next(
            (index for index, name in enumerate(masters) if name.lower() == owner), None
        )
        if owner_index is None:
            continue
        key = (owner_index, object_id)
        if written is not None and key not in written_keys:
            continue  # this record was deliberately skipped by the writer
        entry = found.get(key)
        if entry is None:
            problems.append(f"{change['edid']}: 补丁中缺少该记录")
            continue
        checked += 1
        if entry["damage"] != change["after"]["damage"]:
            problems.append(f"{change['edid']}: 伤害 {entry['damage']} != {change['after']['damage']}")
        if change["after"]["speed"] is not None and entry["speed"] is not None:
            if abs(entry["speed"] - change["after"]["speed"]) > 1e-4:
                problems.append(f"{change['edid']}: 攻速 {entry['speed']} != {change['after']['speed']}")
        if change["after"].get("crit") is not None and entry["crit"] is not None:
            if entry["crit"] != change["after"]["crit"]:
                problems.append(f"{change['edid']}: 暴击 {entry['crit']} != {change['after']['crit']}")
    return {
        "records_in_patch": len(found),
        "checked": checked,
        "masters": len(masters),
        "esl": bool(header["flags"] & 0x200),
        "problems": problems[:40],
        "ok": not problems,
    }
