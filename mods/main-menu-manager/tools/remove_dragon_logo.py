"""Detach the stock 3D dragon emblem from background NIFs, with backups.

Only edits library sources, never deployed resources or the runtime journal.
Supports the Skyrim 83/100 block envelopes used by this library. Unknown
formats fail closed. Texture identity distinguishes the emblem from wallpaper.
"""
from pathlib import Path
import argparse
import hashlib
import json
import struct


class Nif:
    def __init__(self, data):
        self.data = data
        self.pos = data.index(b'\n') + 1
        version, endian, user, count, stream = self.read('IBIII')
        if (version, endian, user) != (0x14020007, 1, 12) or stream not in (83, 100):
            raise ValueError('Unsupported NIF version')
        for _ in range(3):
            self.take(self.read('B')[0])
        types = [self.take(self.read('I')[0]).decode() for _ in range(self.read('H')[0])]
        indices = self.read('H' * count)
        sizes = self.read('I' * count)
        strings, _ = self.read('II')
        for _ in range(strings):
            self.take(self.read('I')[0])
        if self.read('I')[0]:
            raise ValueError('Unsupported NIF groups')
        self.blocks = []
        for index, size in zip(indices, sizes):
            offset = self.pos
            self.blocks.append((types[index], offset, self.take(size)))
        if self.data[self.pos:] != struct.pack('<II', 1, 0):
            raise ValueError('Unexpected root/footer')

    def take(self, size):
        result = self.data[self.pos:self.pos + size]
        if len(result) != size:
            raise ValueError('Truncated NIF')
        self.pos += size
        return result

    def read(self, fmt):
        return struct.unpack('<' + fmt, self.take(struct.calcsize('<' + fmt)))


def uint(blob, offset):
    return struct.unpack_from('<I', blob, offset)[0]


def flags_offset(blob):
    # NiObjectNET: name, extra-data count/list, controller.
    return 12 + 4 * uint(blob, 4)


def patch(data):
    nif = Nif(data)
    textures = set()
    for index, (kind, _, blob) in enumerate(nif.blocks):
        if kind != 'BSShaderTextureSet':
            continue
        size = uint(blob, 4)
        diffuse = blob[8:8 + size].lower().replace(b'\\', b'/')
        if diffuse.removeprefix(b'textures/') == b'interface/objects/logo02_d.dds':
            textures.add(index)
    shaders = set()
    for index, (kind, _, blob) in enumerate(nif.blocks):
        if kind == 'BSLightingShaderProperty':
            # Shader type + NiObjectNET + flags (8) + UV offset/scale (16).
            texture_offset = 40 + 4 * uint(blob, 8)
            if uint(blob, texture_offset) in textures:
                shaders.add(index)
    shapes = set()
    for index, (kind, _, blob) in enumerate(nif.blocks):
        if kind in ('NiTriShape', 'NiTriStrips') and uint(blob, len(blob) - 8) in shaders:
            shapes.add(index)
    if textures and not shapes:
        raise ValueError('Emblem texture found but geometry not recognized')
    output = bytearray(data)
    detached = []
    for index, (kind, offset, blob) in enumerate(nif.blocks):
        if kind not in ('NiNode', 'BSFadeNode'):
            continue
        # NiAVObject: flags (4), transform (52), collision reference (4).
        children = flags_offset(blob) + 60
        count = uint(blob, children)
        if children + 4 + count * 4 + 4 > len(blob):
            raise ValueError('Invalid node children')
        for child in range(count):
            slot = children + 4 + child * 4
            target = uint(blob, slot)
            if target in shapes:
                struct.pack_into('<i', output, offset + slot, -1)
                detached.append({'parent': index, 'shape': target})
    for index in shapes:
        _, offset, blob = nif.blocks[index]
        flags = flags_offset(blob)
        struct.pack_into('<I', output, offset + flags, uint(blob, flags) | 1)
    return bytes(output), detached


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('library', type=Path, help='MainMenuManager directory')
    parser.add_argument('--backup', type=Path, help='New backup directory; omit for read-only audit')
    args = parser.parse_args()
    root = args.library.resolve()
    planned = []
    scanned = 0
    # Include recoverably deleted themes so restoring one cannot revive the logo.
    for category in ('backgrounds', 'deleted-backgrounds'):
        for path in sorted((root / category).rglob('*.nif')):
            if path.is_symlink() or not path.resolve().is_relative_to(root):
                raise ValueError('Linked resource is not supported')
            before = path.read_bytes()
            after, changes = patch(before)
            scanned += 1
            if after != before:
                planned.append((path, before, after, changes))
    report = {'scanned': scanned, 'changed': len(planned), 'applied': bool(args.backup), 'files': []}
    if args.backup:
        args.backup.mkdir(parents=True, exist_ok=False)
    for path, before, after, changes in planned:
        relative = path.relative_to(root)
        if patch(after)[0] != after:
            raise ValueError('Patch is not idempotent')
        entry = {'path': relative.as_posix(), 'detached': changes,
                 'before_sha256': hashlib.sha256(before).hexdigest(),
                 'after_sha256': hashlib.sha256(after).hexdigest()}
        if args.backup:
            backup = args.backup / relative
            backup.parent.mkdir(parents=True, exist_ok=True)
            backup.write_bytes(before)
            if path.read_bytes() != before:
                raise ValueError('Source changed during audit')
            temporary = path.with_suffix('.nif.logo-tmp')
            temporary.write_bytes(after)
            temporary.replace(path)
        report['files'].append(entry)
    if args.backup:
        (args.backup / 'report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
