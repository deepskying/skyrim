"""Build a verified MO2 visual-only override; never touch profiles or install files."""
import hashlib,json,subprocess,sys,zipfile
from paths import ROOT,DATA,MESH,TEX,BUILD
from energy_geometry import VERSION,KEYS

subprocess.run([sys.executable,str(ROOT/'source/verify_release.py'),'--models-only'],check=True,capture_output=True)
files=[MESH/(key+suffix+'.nif') for key in KEYS for suffix in ('','_flight')]
files+=[TEX/'solid.dds',TEX/'redesign08/facets.dds']
assert len(files)==24
release=ROOT/'release';release.mkdir(exist_ok=True)
archive=release/('MagicArrows-Visuals-'+VERSION+'-MO2.zip')
notes=(ROOT/'docs/five-arrow-redesign08.md').read_bytes()+b'\n\n'+(ROOT/'docs/luminous-v4.md').read_bytes()
meta='[General]\ngameName=Skyrim Special Edition\nmodid=0\nversion='+VERSION+'\nnotes=Visual-only override for Magic Arrows. Load after the base mod. Blood arrow is unchanged.\n'
manifest=dict(visual_version=VERSION,base_mod_version='1.1.0',in_game_tested=False,
              files=[dict(path=p.relative_to(DATA).as_posix(),bytes=p.stat().st_size,
                          sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in files])
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for p in files:z.write(p,p.relative_to(DATA).as_posix())
    z.writestr('README.md',notes)
    z.writestr('meta.ini',meta)
    z.writestr('visual-manifest.json',json.dumps(manifest,ensure_ascii=False,indent=2))
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None
    assert len(z.namelist())==len(files)+3
    for f in manifest['files']:assert hashlib.sha256(z.read(f['path'])).hexdigest()==f['sha256']
manifest.update(archive=str(archive),archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest())
(BUILD/'visual-release.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
print(archive)
