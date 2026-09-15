"""Update the existing MO2 mod with a backup and byte-for-byte verification.

Only this mod's runtime assets, README and version metadata are managed. Plugin
activation, profile files, saves and the original game Data folder are untouched.
"""
from pathlib import Path
import configparser,datetime,hashlib,json,re,shutil,subprocess

ROOT=Path(__file__).resolve().parents[1]
MODS=Path(r'C:\Users\linos\Desktop\games\+skyrim\MO2\mods')
# Find the existing plugin so user-organized MO2 folder names remain intact.
candidates=[p.parent for p in MODS.glob('*/ArcaneArsenal.esp') if p.is_file()]
assert len(candidates)==1, f'Expected one installed ArcaneArsenal.esp, found: {candidates}'
DEST=candidates[0]
assert DEST.is_dir() and (DEST/'ArcaneArsenal.esp').is_file(),DEST
running=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',
                        'if (Get-Process SkyrimSE -ErrorAction SilentlyContinue) { exit 1 }'],
                       capture_output=True,creationflags=subprocess.CREATE_NO_WINDOW)
assert running.returncode==0,'Exit Skyrim SE before replacing this mod.'
meta=configparser.ConfigParser();meta.read(ROOT/'packaging/meta.ini',encoding='utf-8')
version=meta['General']['version']
backup=ROOT/'build'/('mo2-before-'+version+'-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S'))
backup.mkdir(parents=True,exist_ok=False)
assets={p.relative_to(ROOT/'data'):p.read_bytes() for p in (ROOT/'data').rglob('*') if p.is_file()}
assert len(assets)==183 and all(p.suffix in ('.esp','.nif','.dds','.pex','.seq') for p in assets)
assets[Path('README.md')]=(ROOT/'README.md').read_bytes()
existing_meta=(DEST/'meta.ini').read_text(encoding='utf-8-sig')
updated_meta,count=re.subn(r'(?m)^version=[^\r\n]*','version='+version,existing_meta)
assert count==1
updated_meta=re.sub(r'(?m)^comments=[^\r\n]*','comments='+meta['General']['comments'],updated_meta)
assets[Path('meta.ini')]=updated_meta.encode('utf-8')
obsolete=[Path('textures/weapons/arcanearsenal')/('frostwyrm_'+s+'.dds')
          for s in ('deep','ice','frost','edge','eye','mouth','n','g')]
obsolete += [Path(rel) for rel in json.loads((ROOT/'source/obsolete_assets.json').read_text(encoding='utf-8'))]
assert all((DEST/rel).resolve().is_relative_to(DEST.resolve()) for rel in obsolete)
changed=[];added=[];removed=[]
for rel,data in assets.items():
    dst=DEST/rel
    assert dst.resolve().is_relative_to(DEST.resolve())
    if dst.exists() and dst.read_bytes()==data:continue
    if dst.exists():
        saved=backup/rel;saved.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(dst,saved);changed.append(str(rel))
    else:added.append(str(rel))
for rel in obsolete:
    dst=DEST/rel
    if dst.exists():
        saved=backup/rel;saved.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(dst,saved);removed.append(str(rel))
try:
    for rel in changed+added:
        dst=DEST/rel;dst.parent.mkdir(parents=True,exist_ok=True);dst.write_bytes(assets[Path(rel)])
    for rel in removed:(DEST/rel).unlink()
    for rel,data in assets.items():assert (DEST/rel).read_bytes()==data,rel
    assert all(not (DEST/rel).exists() for rel in obsolete)
except Exception:
    for rel in changed+removed:shutil.copy2(backup/rel,DEST/rel)
    for rel in added:
        if (DEST/rel).is_file():(DEST/rel).unlink()
    raise
report={'version':version,'destination':str(DEST),'backup':str(backup),'runtime_files_verified':183,
        'changed':changed,'added':added,'removed_obsolete':removed,'verified':True,
        'sha256':{str(rel):hashlib.sha256(data).hexdigest() for rel,data in assets.items()}}
(ROOT/'build/install-report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in report.items() if k!='sha256'},indent=2))
