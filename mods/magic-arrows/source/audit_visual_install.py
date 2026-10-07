"""Read-only audit of effective MO2 mesh/plugin paths and current prototypes."""
import json,hashlib
from pathlib import Path
from paths import BUILD,MODS,GAME
from plugin_records import records,subrecords
report=json.loads((BUILD/'pure-geometry-installation.json').read_text(encoding='utf-8'))
profile=MODS.parent/'profiles'/report['profile']
active=[x[1:] for x in (profile/'modlist.txt').read_text(encoding='utf-8-sig').splitlines() if x.startswith('+')]
def candidates(rel):
    return [p for p in [MODS.parent/'overwrite'/rel]+[MODS/name/rel for name in active]+[GAME/'Data'/rel] if p.is_file()]
for rel in ('MagicArrows.esp','meshes/magicarrows/holy.nif','meshes/magicarrows/holy_flight.nif'):
    print(rel)
    for p in candidates(rel):print(str(p),hashlib.sha256(p.read_bytes()).hexdigest())
for p in candidates('MagicArrows.esp'):
    print('PLUGIN',str(p))
    for r in records(p,{b'AMMO',b'PROJ'}):
        if r['form']&0xfff not in (0x810,0x811,0xa10,0xa11):continue
        d=dict(subrecords(r['data']))
        print(hex(r['form']),r['sig'].decode(),[(k.decode(),v.rstrip(b'\0').decode('utf-8',errors='replace')) for k,v in d.items() if k in (b'FULL',b'EDID',b'MODL')])
        if b'MODL' in d:
            rel=Path('meshes')/d[b'MODL'].rstrip(b'\0').decode()
            for found in candidates(rel):print('RESOLVED',str(found))
plugins=[x[1:] for x in (profile/'plugins.txt').read_text(encoding='utf-8-sig').splitlines() if x.startswith('*')]
for name in plugins:
    choices=candidates(name)
    if not choices:continue
    plugin=choices[0]
    hdr=next(records(plugin))
    masters=[v.rstrip(b'\0').decode(errors='replace') for k,v in subrecords(hdr['data']) if k==b'MAST']
    if 'MagicArrows.esp' not in masters:continue
    index=masters.index('MagicArrows.esp')
    for r in records(plugin,{b'AMMO',b'PROJ'}):
        if r['form']>>24!=index or r['form']&0xffffff not in (0x810,0x811,0xa10,0xa11):continue
        d=dict(subrecords(r['data']));print('OVERRIDE',name,hex(r['form']),[(k.decode(),v.rstrip(b'\0').decode(errors='replace')) for k,v in d.items() if k in (b'EDID',b'FULL',b'MODL')])
