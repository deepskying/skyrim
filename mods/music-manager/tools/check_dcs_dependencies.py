"""Inspect active plugin headers without changing MO2 or loading the game."""
import argparse
import json
import struct
from pathlib import Path

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--mo2', type=Path, required=True)
    p.add_argument('--game', type=Path, required=True)
    p.add_argument('--profile', default='-std-')
    args = p.parse_args()
    profile = args.mo2 / 'profiles' / args.profile
    roots = [args.mo2 / 'overwrite']
    roots += [args.mo2 / 'mods' / line[1:] for line in (profile/'modlist.txt').read_text(encoding='utf-8-sig').splitlines() if line.startswith('+')]
    roots += [args.game / 'Data']
    files = {}
    for root in roots:
        if root.is_dir():
            for f in root.iterdir():
                if f.is_file() and f.suffix.lower() in ('.esp', '.esm', '.esl'):
                    files.setdefault(f.name.casefold(), f)
    result = {'dependents': [], 'missing': [], 'checked': 0}
    for line in (profile/'plugins.txt').read_text(encoding='utf-8-sig').splitlines():
        if not line.startswith('*'):
            continue
        name = line[1:]
        file = files.get(name.casefold())
        if not file:
            result['missing'].append(name)
            continue
        with file.open('rb') as stream:
            head = stream.read(24)
            if head[:4] != b'TES4':
                continue
            body = stream.read(struct.unpack_from('<I', head, 4)[0])
        offset = 0
        while offset + 6 <= len(body):
            kind, length = struct.unpack_from('<4sH', body, offset)
            value = body[offset+6:offset+6+length]
            offset += 6+length
            if kind == b'MAST':
                master = value.rstrip(b'\0').decode('utf-8', errors='replace')
                if master.upper().startswith('DCS'):
                    result['dependents'].append({'plugin':name,'master':master})
        result['checked'] += 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
if __name__ == '__main__':
    main()
