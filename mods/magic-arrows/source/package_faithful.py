"""Verified concept resource packages; optional backed-up MO2 installation."""
import json,hashlib,zipfile,shutil,datetime,sys
from pathlib import Path
from paths import ROOT,BUILD,MODS
round03='--geometric-round03' in sys.argv
redesign08='--five-arrow-redesign' in sys.argv
selected='--geometric-selected' in sys.argv or round03
if redesign08:from five_arrow_redesign import KEYS,VERSION,STAGE
elif round03:from geometric_round03 import KEYS,VERSION
elif selected:from geometric_selected import KEYS,VERSION
else:from faithful_samples import KEYS,VERSION
stage=BUILD/('geometric-selected-05/data' if selected else 'faithful-samples-01/data')
if round03:stage=BUILD/'geometric-round03/data'
if redesign08:stage=BUILD/STAGE
verification=json.loads((BUILD/('verification-redesign08.json' if redesign08 else 'verification-geometric-round03.json' if round03 else 'verification-geometric05.json' if selected else 'verification-faithful01.json')).read_text(encoding='utf-8'))
assert verification['passed']
files=sorted(p for p in stage.rglob('*') if p.is_file())
digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
manifest={p.relative_to(stage).as_posix():digest(p) for p in files}
for entry in verification['files']:assert manifest['meshes/magicarrows/'+entry['file']]==entry['sha256']
prefix='MagicArrows-Five-Arrow-Redesign' if redesign08 else 'MagicArrows-Geometric-Round03' if round03 else 'MagicArrows-Geometric-Selected' if selected else 'MagicArrows-Faithful-Samples'
archive=ROOT/'dist'/f'{prefix}-{VERSION}-MO2.zip';archive.parent.mkdir(exist_ok=True)
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
    for p in files:z.write(p,p.relative_to(stage).as_posix())
    z.writestr('README.md',(ROOT/('docs/five-arrow-redesign08.md' if redesign08 else 'docs/geometric-round03.md' if round03 else 'docs/geometric-scale-061.md' if selected else 'docs/faithful-samples-01.md')).read_text(encoding='utf-8'))
    z.writestr('meta.ini','[General]\nmodid=0\nversion='+VERSION+'\n')
    z.writestr('manifest.json',json.dumps(manifest,indent=2))
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None
    for name,hashvalue in manifest.items():assert hashlib.sha256(z.read(name)).hexdigest()==hashvalue
print(archive)
if '--install' not in sys.argv:sys.exit(0)
prior_path=BUILD/'visual-installation.json'
if prior_path.exists():
    prior=json.loads(prior_path.read_text(encoding='utf-8'))
else:
    # Build reports may have been cleaned; resolve the active MO2 profile and winner.
    import re
    settings=(MODS.parent/'ModOrganizer.ini').read_text(encoding='utf-8-sig')
    match=re.search(r'^selected_profile=@ByteArray\((.+)\)$',settings,re.M)
    assert match,'Cannot determine active MO2 profile'
    profile_name=match.group(1)
    names=[line[1:] for line in (MODS.parent/'profiles'/profile_name/'modlist.txt').read_text(encoding='utf-8-sig').splitlines() if line.startswith('+')]
    rel=Path('meshes/magicarrows')/(KEYS[0]+'.nif')
    target_name=next(name for name in names if (MODS/name/rel).is_file())
    prior=dict(installed=str(MODS/target_name),profile=profile_name)
target=MODS/Path(prior['installed']).name;assert target.is_dir()
profile=MODS.parent/'profiles'/prior['profile']/'modlist.txt';profile_before=profile.read_bytes()
enabled=[line[1:] for line in profile_before.decode('utf-8-sig').splitlines() if line.startswith('+')]
assert target.name in enabled
install=[p for p in files if ('redesign08' if redesign08 else 'geometric05' if selected else 'faithful01') in p.relative_to(stage).parts or p.suffix=='.nif']
for p in files:
    rel=p.relative_to(stage)
    if p not in install:assert (target/rel).is_file() and digest(target/rel)==digest(p)
for key in KEYS:
    for suffix in ('','_flight'):
        rel=Path('meshes/magicarrows')/(key+suffix+'.nif')
        assert not (MODS.parent/'overwrite'/rel).exists()
        winner=next(name for name in enabled if (MODS/name/rel).is_file());assert winner==target.name
def snapshot():
    paths=set((target/'meshes/magicarrows').rglob('*'))|set((target/'textures/magicarrows').rglob('*'))
    paths|={p for p in target.rglob('*') if p.suffix.lower() in ('.dll','.esp','.ini')}
    return {p.relative_to(target).as_posix():digest(p) for p in paths if p.is_file()}
before=snapshot();wanted={p.relative_to(stage).as_posix() for p in install}
retained={}
if round03:
    for key in ('blood','wind','water'):
        for suffix in ('','_flight'):
            name=f'meshes/magicarrows/{key}{suffix}.nif'
            assert name in before
            retained[name]=before[name]
    shared='textures/magicarrows/geometric05/facets.dds'
    assert manifest[shared]==before[shared],'Shared atlas must remain byte-identical for retained wind/water arrows'
backup=MODS.parent.parent/'mod-backups'/((('MagicArrows-Five-Arrow-' if redesign08 else 'MagicArrows-Geometric-' if selected else 'MagicArrows-Faithful-')+VERSION+'-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S')));backup.mkdir(parents=True,exist_ok=False)
added=[]
for p in install:
    rel=p.relative_to(stage);dest=target/rel
    if dest.exists():
        saved=backup/rel;saved.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(dest,saved);assert digest(saved)==before[rel.as_posix()]
    else:added.append(rel.as_posix())
for p in install:
    rel=p.relative_to(stage);dest=target/rel;dest.parent.mkdir(parents=True,exist_ok=True)
    pending=dest.with_suffix(dest.suffix+'.faithful-pending');shutil.copy2(p,pending);pending.replace(dest)
after=snapshot()
assert set(after)==set(before)|wanted
assert all(after[name]==hashvalue for name,hashvalue in before.items() if name not in wanted)
assert all(after[name]==manifest[name] for name in wanted)
assert all(after[name]==hashvalue for name,hashvalue in retained.items())
assert profile.read_bytes()==profile_before
report=dict(sample_version=VERSION,installed=str(target),backup=str(backup),archive=str(archive),
            files_updated=sorted(wanted),new_files=added,protected_files_unchanged=len(set(before)-wanted),
            all_surfaces_self_emissive=True,in_game_tested=False,profile_unchanged=True)
if round03:report['retained_arrows_unchanged']=retained
history=BUILD/('redesign08-installation.json' if redesign08 else 'geometric-round03-installation.json' if round03 else 'geometric05-installation.json' if selected else 'faithful-installation.json')
if history.exists():
    old=json.loads(history.read_text(encoding='utf-8'))
    report['original_backup']=old.get('original_backup',old['backup'])
for out in (history,backup/'installation.json'):
    out.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2))
