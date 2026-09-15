"""Publish only the verified model assets, with no ESP or live install changes."""
import hashlib,json,shutil,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
STAGE=ROOT/'build/staves-geometric';DEST=ROOT/'models/staves-geometric'
report=json.loads((STAGE/'verification.json').read_text(encoding='utf-8'))
assert report['passed'] and len(report['models'])==8
for rel,digest in report['files_sha256'].items():
    src=STAGE/'Data'/rel
    assert hashlib.sha256(src.read_bytes()).hexdigest()==digest,(rel,'Changed since verification')
    dst=DEST/'Data'/rel;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)
shutil.copy2(STAGE/'verification.json',DEST/'verification.json')
shutil.copy2(ROOT/'docs/staves-models.md',DEST/'README.md')
archive=ROOT/'packaging/ArcaneArmory-Staves-Models-0.2.0.zip'
files={p:p.relative_to(DEST).as_posix() for p in DEST.rglob('*') if p.is_file()}
specs=json.loads((ROOT/'source/staves_catalog.json').read_text(encoding='utf-8'))
for spec in specs:
    p=ROOT/'art/staves-geometric'/(spec['key']+'.blend');files[p]='Blender/'+p.name
for name in ('staves-lineup.png','staves-heads.png'):
    p=ROOT/'art/staves-geometric'/name;files[p]='Preview/'+name
for name in ('staves_catalog.json','staves_geometry.py','build_staves.py','prepare_staff_reference.py','render_staves.py','verify_staves.py','package_staves_models.py'):
    p=ROOT/'source'/name;files[p]='Source/'+name
assert all(p.is_file() for p in files)
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for src,rel in files.items():z.write(src,rel)
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None
    assert len(z.namelist())==len(set(z.namelist()))
    for src,rel in files.items():assert z.read(rel)==src.read_bytes()
result={'version':'0.2.0','archive':str(archive),'bytes':archive.stat().st_size,'sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'model_files':8,'packaged_files':len(files),'verified':True,'installed':False}
(STAGE/'package-report.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result,indent=2))
