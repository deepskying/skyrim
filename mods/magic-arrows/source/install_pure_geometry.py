"""Backup and install exactly four authorized sample meshes into active MO2."""
import hashlib,json,shutil,zipfile,datetime,sys
from pathlib import Path
from paths import ROOT,BUILD,MODS
flow='--luminous-v4' in sys.argv
if flow:from luminous_v4 import VERSION,KEYS
else:from pure_geometry_samples import VERSION,KEYS
stage=BUILD/('luminous-v4/data' if flow else 'pure-geometry-02/data')
verification=json.loads((BUILD/('verification-v4.json' if flow else 'verification-pure02.json')).read_text(encoding='utf-8'))
assert verification['passed']
prior=json.loads((BUILD/'visual-installation.json').read_text(encoding='utf-8'))
target=MODS/Path(prior['installed']).name
assert target.is_dir()
profile=MODS.parent/'profiles'/prior['profile']/'modlist.txt'
profile_bytes=profile.read_bytes();lines=profile_bytes.decode('utf-8-sig').splitlines()
assert '+'+target.name in lines
meshfiles=[Path('meshes/magicarrows')/(key+suffix+'.nif') for key in KEYS for suffix in ('','_flight')]
# MO2 modlist is written in descending priority. Confirm this mod wins these paths.
enabled=[line[1:] for line in lines if line.startswith('+')]
for rel in meshfiles:
    winner=next(name for name in enabled if (MODS/name/rel).is_file())
    assert winner==target.name,(rel,winner)
hashfile=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def snapshot():
    selected=set((target/'meshes/magicarrows').rglob('*'))|set((target/'textures/magicarrows').rglob('*'))
    selected|={p for p in target.rglob('*') if p.suffix.lower() in ('.esp','.dll','.ini')}
    return {p.relative_to(target).as_posix():hashfile(p) for p in selected if p.is_file()}
before=snapshot();wanted={r.as_posix() for r in meshfiles}
assert hashfile(target/'textures/magicarrows/solid.dds')==hashfile(stage/'textures/magicarrows/solid.dds')
backup=MODS.parent.parent/'mod-backups'/(('MagicArrows-Luminous-V4-' if flow else 'MagicArrows-PureGeometry-02-')+datetime.datetime.now().strftime('%Y%m%d-%H%M%S'))
backup.mkdir(parents=True,exist_ok=False)
for rel in meshfiles:
    dest=backup/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(target/rel,dest)
    assert hashfile(dest)==before[rel.as_posix()]
for rel in meshfiles:shutil.copy2(stage/rel,target/rel)
after=snapshot()
assert set(before)==set(after)
assert all(after[name]==digest for name,digest in before.items() if name not in wanted)
assert profile.read_bytes()==profile_bytes
for rel in meshfiles:assert hashfile(target/rel)==hashfile(stage/rel)
files=meshfiles+[Path('textures/magicarrows')/(k+'.dds') for k in ('solid','drop','spark','star')]
manifest={r.as_posix():hashfile(stage/r) for r in files}
archive=ROOT/'dist'/f'MagicArrows-{"Luminous" if flow else "PureGeometry"}-{VERSION}-MO2.zip'
archive.parent.mkdir(exist_ok=True)
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
    for rel in files:z.write(stage/rel,rel.as_posix())
    z.writestr('README.md',(ROOT/('docs/luminous-v4.md' if flow else 'docs/pure-geometry-02.md')).read_text(encoding='utf-8'))
    z.writestr('meta.ini','[General]\nmodid=0\nversion='+VERSION+'\n')
    z.writestr('manifest.json',json.dumps(manifest,indent=2))
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None
    for rel,digest in manifest.items():assert hashlib.sha256(z.read(rel)).hexdigest()==digest
report=dict(visual_version=VERSION,installed=str(target),backup=str(backup),profile=prior['profile'],
            files_updated=sorted(wanted),protected_files_unchanged=len(before)-len(wanted),
            profile_unchanged=True,all_surfaces_self_emissive=True,in_game_tested=False,archive=str(archive))
(backup/'installation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
(BUILD/('luminous-v4-installation.json' if flow else 'pure-geometry-installation.json')).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2))
