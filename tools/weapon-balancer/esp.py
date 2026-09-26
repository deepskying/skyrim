"""Minimal, tolerant TES4 (Skyrim SE) plugin reader plus localized strings lookup.

Only what the weapon balancer needs: read the master list, walk WEAP records,
walk their subrecords, and resolve localized FULL names from the matching
``.STRINGS`` file. Structurally odd records are skipped instead of raising:
real load orders contain a few of them (the Unofficial Patch is one), and one
bad record must not abort a 900-plugin scan.
"""
from __future__ import annotations

import struct
import zlib
from pathlib import Path

HEADER = struct.Struct("<4sIIIIHH")
LOCALIZED = 0x80
COMPRESSED = 0x40000
NON_PLAYABLE = 0x04


def read_header(path: Path) -> dict:
    """Return the TES4 header: masters, flags, version and the plugin name."""
    with open(path, "rb") as handle:
        head = handle.read(24)
        if len(head) < 24:
            raise ValueError("file is too small to be a plugin")
        sig, size, flags, _form, _rev, version, _unknown = HEADER.unpack(head)
        if sig != b"TES4":
            raise ValueError("missing TES4 record header")
        handle.seek(24)
        payload = handle.read(size)

    masters: list[str] = []
    author = ""
    description = ""
    pos = 0
    while pos + 6 <= len(payload):
        sig, length = struct.unpack_from("<4sH", payload, pos)
        pos += 6
        if pos + length > len(payload):
            break
        value = payload[pos : pos + length]
        pos += length
        if sig == b"MAST":
            masters.append(value.rstrip(b"\0").decode("utf-8", "replace"))
        elif sig == b"CNAM":
            author = value.rstrip(b"\0").decode("utf-8", "replace")
        elif sig == b"SNAM":
            description = value.rstrip(b"\0").decode("utf-8", "replace")
    return {
        "masters": masters,
        "flags": flags,
        "version": version,
        "localized": bool(flags & LOCALIZED),
        "author": author,
        "description": description,
    }


def iter_records(data: bytes, wanted: set[bytes] | None = None):
    """Yield ``(signature, form_id, flags, version, payload)`` per record."""

    def walk(start: int, end: int):
        pos = start
        while pos + 24 <= end:
            sig = data[pos : pos + 4]
            size = struct.unpack_from("<I", data, pos + 4)[0]
            if sig == b"GRUP":
                if size < 24 or pos + size > end:
                    return
                label = data[pos + 8 : pos + 12]
                kind = struct.unpack_from("<i", data, pos + 12)[0]
                if wanted is None or kind != 0 or label in wanted:
                    yield from walk(pos + 24, pos + size)
                pos += size
                continue
            if pos + 24 + size > end:
                return
            flags = struct.unpack_from("<I", data, pos + 8)[0]
            form = struct.unpack_from("<I", data, pos + 12)[0]
            if wanted is None or sig in wanted:
                payload = data[pos + 24 : pos + 24 + size]
                if flags & COMPRESSED and len(payload) >= 4:
                    try:
                        payload = zlib.decompress(payload[4:])
                    except zlib.error:
                        payload = b""
                version = struct.unpack_from("<H", data, pos + 20)[0]
                yield sig, form, flags & ~COMPRESSED, version, payload
            pos += 24 + size

    yield from walk(0, len(data))


def iter_subrecords(payload: bytes):
    """Yield ``(signature, value)`` pairs, stopping at the first malformed one."""
    pos = 0
    extended: int | None = None
    total = len(payload)
    while pos + 6 <= total:
        sig, size = struct.unpack_from("<4sH", payload, pos)
        pos += 6
        if sig == b"XXXX":
            if size < 4 or pos + 4 > total:
                return
            extended = struct.unpack_from("<I", payload, pos)[0]
            pos += 4
            continue
        if extended is not None:
            size, extended = extended, None
        if pos + size > total:
            return
        yield sig, payload[pos : pos + size]
        pos += size


def sub_map(payload: bytes) -> dict[bytes, bytes]:
    """Return the record's subrecords keyed by signature (later wins)."""
    result: dict[bytes, bytes] = {}
    for sig, value in iter_subrecords(payload):
        result[sig] = value
    return result


def decode_text(value: bytes) -> str:
    """Decode a plugin string (null-terminated, UTF-8, with GBK fallback)."""
    value = value.split(b"\0")[0]
    for encoding in ("utf-8", "cp936", "latin-1"):
        try:
            return value.decode(encoding)
        except UnicodeDecodeError:
            continue
    return value.decode("utf-8", "replace")


def lstring(value: bytes) -> str:
    """Decode a string subrecord of a non-localized plugin.

    Skyrim stores these as plain null-terminated UTF-8; the subrecord size
    already carries the length, so there is no length prefix to strip.
    """
    return decode_text(value)


def load_string_table(path: Path) -> dict[int, str]:
    """Parse a Skyrim ``.STRINGS`` file into ``{string id: text}``.

    Layout: ``uint32 count`` followed by ``count`` pairs of
    ``(uint32 string id, uint32 offset)``, then the null-terminated UTF-8 blob
    the offsets point into.
    """
    data = path.read_bytes()
    if len(data) < 8:
        return {}
    count = struct.unpack_from("<I", data, 0)[0]
    if count == 0 or 8 + 8 * count > len(data):
        return {}
    blob = 8 + 8 * count
    table: dict[int, str] = {}
    for index in range(count):
        string_id, offset = struct.unpack_from("<II", data, 8 + 8 * index)
        start = blob + offset
        if start >= len(data):
            continue
        end = data.find(b"\0", start)
        if end < 0:
            end = len(data)
        table[string_id] = data[start:end].decode("utf-8", "replace")
    return table
