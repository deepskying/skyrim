"""Read active creature plugins for manual encounter-pool curation.

Produces a report only; never enables records or modifies MO2. NPC templates
are reported with their original names, flags, level and attached script.
"""
from pathlib import Path
import json
import re
import struct
import sys
from build import REPO, GAME_ROOT, ROOT
from plugin_records import records, subrecords, edid

sys.path.insert(0, str(REPO / 'tools/weapon-balancer'))
import scan
import esp

DENY = re.compile(r'audio|sound|voice|pet|template|test|dummy|summon|tamed|domestic|passive|friendly|donotuse|nouse|delete|_seq|newgame|pup|cub|baby|_midden|_dush|_mor\b|_narzu|potema|eldergleam|harkon|DA02', re.I)

def inventory():
    mo2 = GAME_ROOT / 'MO2'
    paths = scan.profile_paths(mo2, None)
    index = scan.plugin_index(paths['mods_dir'], GAME_ROOT / 'SkyrimSE/Data', scan.mod_priority(paths['modlist']))
    active = [line.strip()[1:] for line in paths['plugins'].read_text(encoding='utf-8-sig').splitlines() if line.startswith('*')]
    selected = [name for name in active if name.lower().startswith('mihail') or name in
                ('1KwamaCreatures.esp', 'Age of Beasts - Spino.esp', 'Monster Mod SE.esp',
                 'MorrowindCreatures.esl', 'SirenCreatures.esp', 'Skyrim Immersive Creatures Special Edition.esp')]
    report = {}
    for name in selected:
        path = index[name.lower()]
        masters = esp.read_header(path)['masters']
        items = []
        for row in records(path, {b'NPC_'}):
            if row['form'] >> 24 != len(masters):
                continue
            parts = dict(subrecords(row['data']))
            config = parts.get(b'ACBS', bytes(24))
            flags, = struct.unpack_from('<I', config)
            full = parts.get(b'FULL', b'').rstrip(b'\0')
            try:
                full = full.decode('utf8')
            except UnicodeDecodeError:
                full = full.decode('gb18030', errors='replace')
            script = ''
            if b'VMAD' in parts:
                raw = parts[b'VMAD']
                if struct.unpack_from('<H', raw, 4)[0]:
                    length, = struct.unpack_from('<H', raw, 6)
                    script = raw[8:8+length].decode('utf8', errors='replace')
            items.append(dict(form=f'0x{row["form"] & 0xFFFFFF:X}', edid=edid(row), name=full,
                              flags=flags, record_flags=row['flags'],
                              level=struct.unpack_from('<h', config, 8)[0],
                              minimum=struct.unpack_from('<H', config, 10)[0],
                              maximum=struct.unpack_from('<H', config, 12)[0],
                              aggression=parts.get(b'AIDT', bytes(1))[0],
                              template_flags=struct.unpack_from('<H', config, 18)[0],
                              scripted=b'VMAD' in parts, script=script))
        report[name] = items
    return report

def rejection(item):
    if item['record_flags'] & 0x20:
        return 'deleted'
    if item['flags'] & (0x2 | 0x20 | 0x800 | 0x20000000 | 0x80000000):
        return 'essential/unique/protected/ghost/invulnerable'
    if DENY.search(item['edid']):
        return 'special-purpose name'
    return ''

if __name__ == '__main__':
    report = inventory()
    target = ROOT / 'build/creature-inventory.json'
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf8')
    print(f'{len(report)} active plugins; {sum(map(len, report.values()))} NPC templates')
    print(target)
