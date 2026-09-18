"""Package only the collection's runtime assets and user instructions."""
from pathlib import Path
import hashlib,json,zipfile,struct,configparser
ROOT=Path(__file__).resolve().parents[1]
from release_assets import runtime_paths
metadata=configparser.ConfigParser();metadata.read(ROOT/'packaging/meta.ini',encoding='utf-8')
version=metadata['General']['version']
archive=ROOT/('packaging/ArcaneArmory-'+version+'.zip')
archive.parent.mkdir(parents=True,exist_ok=True)
assets=runtime_paths()
assert len([p for p in assets if p.suffix=='.esp'])==1
assert len([p for p in assets if p.suffix=='.nif'])==178
assert len([p for p in assets if p.suffix=='.dds'])==43
assert len([p for p in assets if p.suffix=='.pex'])==3
assert len([p for p in assets if p.suffix=='.seq'])==1
assert len([p for p in assets if p.suffix=='.dll'])==1
assert all(p.suffix.lower() in {'.esp','.nif','.dds','.pex','.seq','.dll'} for p in assets)
assert not any((ROOT/'data'/rel).exists() for rel in json.loads((ROOT/'source/obsolete_assets.json').read_text(encoding='utf-8')))
plugin=(ROOT/'data/ArcaneArsenal.esp').read_bytes()
assert plugin[:4]==b'TES4' and struct.unpack_from('<I',plugin,8)[0]&0x200, 'ESL flag missing'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as package:
    for path in assets:package.write(path,path.relative_to(ROOT/'data').as_posix())
    package.write(ROOT/'README.md','README.md')
    package.write(ROOT/'docs/staves-prototype.md','docs/staves-prototype.md')
    package.write(ROOT/'art/arcane-staves/lineup.png','art/arcane-staves/lineup.png')
    package.write(ROOT/'packaging/meta.ini','meta.ini')
with zipfile.ZipFile(archive) as package:
    assert package.testzip() is None
    for path in assets:assert package.read(path.relative_to(ROOT/'data').as_posix())==path.read_bytes()
    assert package.read('README.md')==(ROOT/'README.md').read_bytes()
    assert package.read('meta.ini')==(ROOT/'packaging/meta.ini').read_bytes()
report={'archive':str(archive),'bytes':archive.stat().st_size,'sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'runtime_files':len(assets),'verified':True}
(ROOT/'build/package-report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2))
