"""Append missing active weapon rules to the user's existing SPID item list.

Use --check for read-only validation. Existing lines, including other mods and
historical rules, are preserved byte-for-byte. No duplicate DISTR file is installed.
The chance is the literal INI value 0.01, matching the user's established rules.
"""
from pathlib import Path
import argparse,datetime,hashlib,json,re
from plugin_records import records,edid

ROOT=Path(__file__).resolve().parents[1]
TARGET=Path('C:/Users/linos/Desktop/games/+skyrim/MO2/mods/功能模组-物品分发-SPID+CID配置-🟪🟨/-item_DISTR.ini')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check',action='store_true')
    parser.add_argument('--target',type=Path,default=TARGET)
    args=parser.parse_args()
    catalog=json.loads((ROOT/'source/catalog.json').read_text(encoding='utf-8'))
    weapons_count=len(catalog)
    shields=json.loads((ROOT/'source/shields_catalog.json').read_text(encoding='utf-8'))
    catalog+=shields
    plugin={edid(r):r['form'] for r in records(ROOT/'data/ArcaneArsenal.esp') if r['sig'] in (b'WEAP',b'ARMO')}
    assert set(plugin)=={'AA'+s['key'] for s in catalog}
    path=args.target.resolve();raw=path.read_bytes()
    # Decode for parsing, retaining the original bytes when appending.
    if raw.startswith(b'\xff\xfe'):encoding='utf-16-le';bom=b'\xff\xfe'
    elif raw.startswith(b'\xfe\xff'):encoding='utf-16-be';bom=b'\xfe\xff'
    else:encoding='utf-8';bom=b'\xef\xbb\xbf' if raw.startswith(b'\xef\xbb\xbf') else b''
    text=raw[len(bom):].decode(encoding)
    newline='\r\n' if '\r\n' in text else '\n'
    existing=re.findall(r'^\s*Item\s*=\s*([^|\r\n]+)\|([^\r\n]+)',text,re.M)
    assigned={token.strip().casefold() for token,tail in existing}
    missing=[]
    for spec in catalog:
        name='AA'+spec['key'];local=plugin[name]&0xffffff
        # Support either existing EditorIDs or plugin-local FormIDs.
        aliases={name.casefold(),f'0x{local:X}~ArcaneArsenal.esp'.casefold(),f'0x{local:06X}~ArcaneArsenal.esp'.casefold()}
        if aliases.isdisjoint(assigned):missing.append(spec)
    if args.check:
        assert not missing,[s['key'] for s in missing]
        print(json.dumps({'passed':True,'active_items':len(catalog),'active_weapons':weapons_count,'active_shields':len(shields),'all_active_items_distributed':True}))
        return
    if not missing:
        print(json.dumps({'changed':False,'missing':0,'active_items':len(catalog),'active_weapons':weapons_count,'active_shields':len(shields)}))
        return
    stamp=datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    backup=ROOT/'build'/('spid-before-'+stamp+'.ini');backup.write_bytes(raw)
    suffix=('' if not text or text.endswith(('\r','\n')) else newline)+newline
    suffix+='; Arcane Armory - additional active equipment'+newline
    added=[]
    for spec in missing:
        rule='Item = AA'+spec['key']+'|NONE|NONE|NONE|NONE|1|0.01'
        suffix+='; '+spec['name']+newline+rule+newline;added.append(rule)
    updated=raw+suffix.encode(encoding)
    assert path.read_bytes()==raw,'SPID file changed concurrently; re-run against the current contents.'
    try:
        path.write_bytes(updated)
        assert path.read_bytes()==updated
    except Exception:
        path.write_bytes(raw)
        raise
    # Exact prefix preservation proves no existing config was rewritten.
    assert updated[:len(raw)]==raw
    final=updated[len(bom):].decode(encoding)
    for rule in added:assert final.splitlines().count(rule)==1
    report={'passed':True,'path':str(path),'backup':str(backup),'added':added,
            'literal_chance':'0.01','active_items':len(catalog),'active_weapons':weapons_count,'active_shields':len(shields),'original_bytes_preserved':True,
            'sha256':hashlib.sha256(updated).hexdigest()}
    (ROOT/'build/spid-sync-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=True))


if __name__=='__main__':main()
